from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.deps import admin_only, get_current_user
from app.database import get_db
from app.models import Department, Employee, User
from app.schemas import DepartmentIn, DepartmentOut, DepartmentUpdate
from app.services import audit

router = APIRouter(prefix="/departments", tags=["departments"])


@router.get("", response_model=list[DepartmentOut])
def list_departments(db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    return db.scalars(select(Department).order_by(Department.name)).all()


@router.post("", response_model=DepartmentOut, status_code=201)
def create_department(data: DepartmentIn, request: Request, db: Session = Depends(get_db),
                      admin: User = Depends(admin_only)):
    if db.scalar(select(Department.id).where(
            (func.lower(Department.name) == data.name.lower()) | (func.lower(Department.code) == data.code.lower()))):
        raise HTTPException(409, "Department name or code already exists")
    if data.head_id and not db.get(Employee, data.head_id):
        raise HTTPException(400, "Department head not found")
    dep = Department(**data.model_dump())
    db.add(dep)
    db.flush()
    audit.log(db, admin, "create", "department", dep.id, data.model_dump(), request)
    db.commit()
    return dep


@router.put("/{dep_id}", response_model=DepartmentOut)
def update_department(dep_id: int, data: DepartmentUpdate, request: Request, db: Session = Depends(get_db),
                      admin: User = Depends(admin_only)):
    dep = db.get(Department, dep_id)
    if not dep:
        raise HTTPException(404, "Department not found")
    changes = data.model_dump(exclude_unset=True)
    if changes.get("head_id") and not db.get(Employee, changes["head_id"]):
        raise HTTPException(400, "Department head not found")
    for k, v in changes.items():
        setattr(dep, k, v)
    audit.log(db, admin, "update", "department", dep.id, changes, request)
    db.commit()
    return dep


@router.delete("/{dep_id}", status_code=204)
def delete_department(dep_id: int, request: Request, hard: bool = False, db: Session = Depends(get_db),
                      admin: User = Depends(admin_only)):
    dep = db.get(Department, dep_id)
    if not dep:
        raise HTTPException(404, "Department not found")
    has_staff = db.scalar(select(func.count(Employee.id)).where(Employee.department_id == dep_id))
    if hard:
        if has_staff:
            raise HTTPException(409, "Department still has employees; deactivate it instead")
        db.delete(dep)
        audit.log(db, admin, "delete", "department", dep_id, request=request)
    else:
        dep.is_active = False
        audit.log(db, admin, "deactivate", "department", dep_id, request=request)
    db.commit()
