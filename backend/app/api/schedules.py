from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import or_, select
from sqlalchemy.orm import Session, joinedload

from app.core.deps import admin_only, staff_only
from app.database import get_db
from app.models import Camera, Department, Employee, Schedule, ScheduleAssignment, User
from app.schemas import AssignmentIn, AssignmentOut, ScheduleIn, ScheduleOut, ScheduleUpdate
from app.services import audit

router = APIRouter(prefix="/schedules", tags=["schedules"])


def _load(db, sid):
    return db.scalar(select(Schedule).options(joinedload(Schedule.department), joinedload(Schedule.camera))
                     .where(Schedule.id == sid))


def _check_refs(db, department_id, camera_id):
    if department_id and not db.get(Department, department_id):
        raise HTTPException(400, "Department not found")
    if camera_id and not db.get(Camera, camera_id):
        raise HTTPException(400, "Camera not found")


@router.get("", response_model=list[ScheduleOut])
def list_schedules(department_id: int | None = None, db: Session = Depends(get_db), _: User = Depends(staff_only)):
    q = select(Schedule).options(joinedload(Schedule.department), joinedload(Schedule.camera)).order_by(
        Schedule.department_id, Schedule.start_time)
    if department_id:
        q = q.where(Schedule.department_id == department_id)
    return db.scalars(q).all()


@router.post("", response_model=ScheduleOut, status_code=201)
def create_schedule(data: ScheduleIn, request: Request, db: Session = Depends(get_db), admin: User = Depends(admin_only)):
    _check_refs(db, data.department_id, data.camera_id)
    s = Schedule(**data.model_dump())
    db.add(s)
    db.flush()
    audit.log(db, admin, "create", "schedule", s.id, {"name": s.name}, request)
    db.commit()
    return _load(db, s.id)


@router.put("/{sid}", response_model=ScheduleOut)
def update_schedule(sid: int, data: ScheduleUpdate, request: Request, db: Session = Depends(get_db),
                    admin: User = Depends(admin_only)):
    s = _load(db, sid)
    if not s:
        raise HTTPException(404, "Schedule not found")
    changes = data.model_dump(exclude_unset=True)
    _check_refs(db, changes.get("department_id"), changes.get("camera_id"))
    if "working_days" in changes:
        days = changes["working_days"] or []
        if not days or any(d < 0 or d > 6 for d in days):
            raise HTTPException(400, "working_days must be 0 (Mon) to 6 (Sun)")
        changes["working_days"] = sorted(set(days))
    for k, v in changes.items():
        setattr(s, k, v)
    if s.end_time <= s.start_time:
        raise HTTPException(400, "end_time must be after start_time")
    audit.log(db, admin, "update", "schedule", s.id, {k: str(v) for k, v in changes.items()}, request)
    db.commit()
    return _load(db, sid)


@router.delete("/{sid}", status_code=204)
def deactivate_schedule(sid: int, request: Request, db: Session = Depends(get_db), admin: User = Depends(admin_only)):
    s = db.get(Schedule, sid)
    if not s:
        raise HTTPException(404, "Schedule not found")
    s.is_active = False
    audit.log(db, admin, "deactivate", "schedule", sid, request=request)
    db.commit()


@router.get("/{sid}/assignments", response_model=list[AssignmentOut])
def list_assignments(sid: int, db: Session = Depends(get_db), _: User = Depends(staff_only)):
    return db.scalars(select(ScheduleAssignment).options(joinedload(ScheduleAssignment.employee))
                      .where(ScheduleAssignment.schedule_id == sid)
                      .order_by(ScheduleAssignment.effective_from.desc())).all()


def _overlaps(a: Schedule, b: Schedule) -> bool:
    return a.start_time < b.end_time and b.start_time < a.end_time and bool(set(a.working_days) & set(b.working_days))


@router.post("/{sid}/assignments", response_model=list[AssignmentOut], status_code=201)
def assign(sid: int, data: AssignmentIn, request: Request, db: Session = Depends(get_db), admin: User = Depends(admin_only)):
    s = db.get(Schedule, sid)
    if not s or not s.is_active:
        raise HTTPException(404, "Active schedule not found")
    if data.effective_to and data.effective_to < data.effective_from:
        raise HTTPException(400, "effective_to is before effective_from")
    created = []
    for eid in dict.fromkeys(data.employee_ids):
        emp = db.get(Employee, eid)
        if not emp:
            raise HTTPException(400, f"Employee {eid} not found")
        if emp.department_id != s.department_id:
            raise HTTPException(400, f"{emp.employee_code} belongs to a different department than this schedule")
        others = db.scalars(
            select(Schedule).join(ScheduleAssignment, ScheduleAssignment.schedule_id == Schedule.id)
            .where(ScheduleAssignment.employee_id == eid, Schedule.is_active.is_(True), Schedule.id != s.id,
                   or_(ScheduleAssignment.effective_to.is_(None), ScheduleAssignment.effective_to >= data.effective_from),
                   *([ScheduleAssignment.effective_from <= data.effective_to] if data.effective_to else []))).all()
        for o in others:
            if _overlaps(s, o):
                raise HTTPException(400, f"{emp.employee_code} already has an overlapping session: {o.name}")
        if db.scalar(select(ScheduleAssignment.id).where(
                ScheduleAssignment.schedule_id == sid, ScheduleAssignment.employee_id == eid,
                ScheduleAssignment.effective_from == data.effective_from)):
            continue
        a = ScheduleAssignment(schedule_id=sid, employee_id=eid, effective_from=data.effective_from,
                               effective_to=data.effective_to)
        db.add(a)
        created.append(a)
    db.flush()
    audit.log(db, admin, "assign", "schedule", sid, {"employees": data.employee_ids}, request)
    db.commit()
    return db.scalars(select(ScheduleAssignment).options(joinedload(ScheduleAssignment.employee))
                      .where(ScheduleAssignment.id.in_([a.id for a in created]))).all() if created else []


@router.delete("/assignments/{aid}", status_code=204)
def remove_assignment(aid: int, request: Request, db: Session = Depends(get_db), admin: User = Depends(admin_only)):
    a = db.get(ScheduleAssignment, aid)
    if not a:
        raise HTTPException(404, "Assignment not found")
    db.delete(a)
    audit.log(db, admin, "unassign", "schedule", a.schedule_id, {"employee_id": a.employee_id}, request)
    db.commit()
