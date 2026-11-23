from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import delete, func, or_, select
from sqlalchemy.orm import Session, joinedload

from app.core.deps import admin_only, get_current_user, staff_only
from app.core.security import hash_password
from app.database import get_db
from app.models import (Department, Employee, EmploymentStatus, FaceEmbedding, Schedule,
                        ScheduleAssignment, User)
from app.schemas import EmployeeCreate, EmployeeOut, EmployeeUpdate, ScheduleOut
from app.services import access, audit

router = APIRouter(prefix="/employees", tags=["employees"])


def _load(db, emp_id):
    return db.scalar(select(Employee).options(joinedload(Employee.department), joinedload(Employee.user),
                                              joinedload(Employee.supervisor)).where(Employee.id == emp_id))


@router.get("", response_model=list[EmployeeOut])
def list_employees(q: str | None = None, department_id: int | None = None, status: EmploymentStatus | None = None,
                   db: Session = Depends(get_db), user: User = Depends(staff_only)):
    stmt = (select(Employee).options(joinedload(Employee.department), joinedload(Employee.user),
                                     joinedload(Employee.supervisor))
            .where(access.scope_clause(db, user)).order_by(Employee.employee_code))
    if q:
        like = f"%{q}%"
        stmt = stmt.where(or_(Employee.full_name.ilike(like), Employee.employee_code.ilike(like),
                              Employee.email.ilike(like)))
    if department_id:
        stmt = stmt.where(Employee.department_id == department_id)
    if status:
        stmt = stmt.where(Employee.status == status)
    return db.scalars(stmt).all()


@router.post("", response_model=EmployeeOut, status_code=201)
def create_employee(data: EmployeeCreate, request: Request, db: Session = Depends(get_db),
                    admin: User = Depends(admin_only)):
    if db.scalar(select(Employee.id).where(Employee.employee_code == data.employee_code)):
        raise HTTPException(409, "Employee ID already exists")
    if db.scalar(select(Employee.id).where(Employee.email == data.email)):
        raise HTTPException(409, "Employee email already exists")
    if not db.get(Department, data.department_id):
        raise HTTPException(400, "Department not found")
    if data.supervisor_id and not db.get(Employee, data.supervisor_id):
        raise HTTPException(400, "Supervisor not found")
    user = None
    if data.account:
        if db.scalar(select(User.id).where(User.email == data.account.email)):
            raise HTTPException(409, "Login email already in use")
        user = User(email=data.account.email, password_hash=hash_password(data.account.password),
                    role=data.account.role, is_active=data.account.is_active)
        db.add(user)
        db.flush()
    emp = Employee(**data.model_dump(exclude={"account", "face_consent"}),
                   user_id=user.id if user else None, face_consent=data.face_consent,
                   face_consent_at=datetime.now(timezone.utc) if data.face_consent else None)
    db.add(emp)
    db.flush()
    audit.log(db, admin, "create", "employee", emp.id, {"employee_code": emp.employee_code}, request)
    db.commit()
    return _load(db, emp.id)


@router.get("/{employee_id}", response_model=EmployeeOut)
def get_employee(employee_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    access.assert_access(db, user, employee_id)
    emp = _load(db, employee_id)
    if not emp:
        raise HTTPException(404, "Employee not found")
    return emp


@router.put("/{employee_id}", response_model=EmployeeOut)
def update_employee(employee_id: int, data: EmployeeUpdate, request: Request, db: Session = Depends(get_db),
                    admin: User = Depends(admin_only)):
    emp = _load(db, employee_id)
    if not emp:
        raise HTTPException(404, "Employee not found")
    changes = data.model_dump(exclude_unset=True, exclude={"account"})
    if "email" in changes and changes["email"]:
        changes["email"] = changes["email"].lower()
        if db.scalar(select(Employee.id).where(Employee.email == changes["email"], Employee.id != emp.id)):
            raise HTTPException(409, "Employee email already exists")
    if changes.get("department_id") and not db.get(Department, changes["department_id"]):
        raise HTTPException(400, "Department not found")
    if changes.get("supervisor_id") == emp.id:
        raise HTTPException(400, "Employee cannot supervise themselves")
    if "face_consent" in changes:
        if changes["face_consent"] and not emp.face_consent:
            emp.face_consent_at = datetime.now(timezone.utc)
        if not changes["face_consent"]:   # consent withdrawn -> erase biometrics
            db.execute(delete(FaceEmbedding).where(FaceEmbedding.employee_id == emp.id))
    for k, v in changes.items():
        setattr(emp, k, v)
    if data.account:
        a = data.account.model_dump(exclude_unset=True)
        if not emp.user:
            if not (a.get("email") and a.get("password")):
                raise HTTPException(400, "Email and password are required to create a login")
            emp.user = User(email=a["email"].lower(), password_hash=hash_password(a["password"]),
                            role=a.get("role") or "employee", is_active=a.get("is_active", True))
        else:
            if a.get("email"):
                if db.scalar(select(User.id).where(User.email == a["email"].lower(), User.id != emp.user.id)):
                    raise HTTPException(409, "Login email already in use")
                emp.user.email = a["email"].lower()
            if a.get("password"):
                emp.user.password_hash = hash_password(a["password"])
            if a.get("role"):
                emp.user.role = a["role"]
            if "is_active" in a and a["is_active"] is not None:
                emp.user.is_active = a["is_active"]
    audit.log(db, admin, "update", "employee", emp.id,
              {"fields": list(changes) + (["account"] if data.account else [])}, request)
    db.commit()
    return _load(db, emp.id)


@router.delete("/{employee_id}", status_code=204)
def deactivate_employee(employee_id: int, request: Request, db: Session = Depends(get_db),
                        admin: User = Depends(admin_only)):
    emp = _load(db, employee_id)
    if not emp:
        raise HTTPException(404, "Employee not found")
    emp.status = EmploymentStatus.inactive
    if emp.user:
        emp.user.is_active = False
    db.execute(delete(FaceEmbedding).where(FaceEmbedding.employee_id == emp.id))  # retention policy
    audit.log(db, admin, "deactivate", "employee", emp.id, request=request)
    db.commit()


@router.get("/{employee_id}/schedules", response_model=list[ScheduleOut])
def employee_schedules(employee_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    access.assert_access(db, user, employee_id)
    from app.utils.timeutil import today_local
    t = today_local()
    rows = db.scalars(
        select(Schedule).join(ScheduleAssignment, ScheduleAssignment.schedule_id == Schedule.id)
        .options(joinedload(Schedule.department), joinedload(Schedule.camera))
        .where(ScheduleAssignment.employee_id == employee_id, Schedule.is_active.is_(True),
               or_(ScheduleAssignment.effective_to.is_(None), ScheduleAssignment.effective_to >= t))
        .order_by(Schedule.start_time)).all()
    return list({s.id: s for s in rows}.values())
