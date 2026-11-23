from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.core.deps import admin_only, get_current_user
from app.database import get_db
from app.models import Employee, LeaveRequest, LeaveStatus, LeaveType, Role, User
from app.schemas import LeaveIn, LeaveOut, LeaveReviewIn, LeaveTypeIn, LeaveTypeOut
from app.services import access, audit
from app.services.attendance_service import finalize
from app.utils.timeutil import today_local

router = APIRouter(prefix="/leave", tags=["leave"])


def _load(db, lid):
    return db.scalar(select(LeaveRequest).options(joinedload(LeaveRequest.employee), joinedload(LeaveRequest.leave_type))
                     .where(LeaveRequest.id == lid))


@router.get("/types", response_model=list[LeaveTypeOut])
def leave_types(db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    return db.scalars(select(LeaveType).where(LeaveType.is_active.is_(True)).order_by(LeaveType.name)).all()


@router.post("/types", response_model=LeaveTypeOut, status_code=201)
def add_leave_type(data: LeaveTypeIn, db: Session = Depends(get_db), admin: User = Depends(admin_only)):
    if db.scalar(select(LeaveType.id).where(LeaveType.name.ilike(data.name))):
        raise HTTPException(409, "Leave type already exists")
    t = LeaveType(name=data.name)
    db.add(t)
    db.commit()
    return t


@router.get("", response_model=list[LeaveOut])
def list_leave(status: LeaveStatus | None = None, employee_id: int | None = None,
               db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    q = (select(LeaveRequest).join(Employee, Employee.id == LeaveRequest.employee_id)
         .options(joinedload(LeaveRequest.employee), joinedload(LeaveRequest.leave_type))
         .where(access.scope_clause(db, user)).order_by(LeaveRequest.created_at.desc()).limit(500))
    if status:
        q = q.where(LeaveRequest.status == status)
    if employee_id:
        q = q.where(LeaveRequest.employee_id == employee_id)
    return db.scalars(q).all()


@router.post("", response_model=LeaveOut, status_code=201)
def submit_leave(data: LeaveIn, request: Request, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    if data.employee_id and user.role == Role.admin:
        emp = db.get(Employee, data.employee_id)
    else:
        emp = access.my_employee(db, user)
    if not emp:
        raise HTTPException(400, "No employee profile is linked to this account")
    if user.role == Role.employee and data.start_date < today_local():
        raise HTTPException(400, "Leave cannot start in the past; ask your supervisor for a correction")
    lt = db.get(LeaveType, data.leave_type_id)
    if not lt or not lt.is_active:
        raise HTTPException(400, "Invalid leave type")
    clash = db.scalar(select(LeaveRequest.id).where(
        LeaveRequest.employee_id == emp.id, LeaveRequest.status.in_([LeaveStatus.pending, LeaveStatus.approved]),
        LeaveRequest.start_date <= data.end_date, LeaveRequest.end_date >= data.start_date).limit(1))
    if clash:
        raise HTTPException(409, "You already have a leave request covering one or more of these days")
    lr = LeaveRequest(employee_id=emp.id, leave_type_id=lt.id, start_date=data.start_date,
                      end_date=data.end_date, reason=data.reason)
    db.add(lr)
    db.flush()
    audit.log(db, user, "submit", "leave", lr.id, request=request)
    db.commit()
    return _load(db, lr.id)


@router.patch("/{lid}/review", response_model=LeaveOut)
def review_leave(lid: int, data: LeaveReviewIn, request: Request, db: Session = Depends(get_db),
                 user: User = Depends(get_current_user)):
    if user.role == Role.employee:
        raise HTTPException(403, "Not allowed")
    lr = _load(db, lid)
    if not lr:
        raise HTTPException(404, "Leave request not found")
    access.assert_access(db, user, lr.employee_id)
    me = access.my_employee(db, user)
    if me and me.id == lr.employee_id and user.role != Role.admin:
        raise HTTPException(403, "You cannot review your own leave request")
    if lr.status != LeaveStatus.pending:
        raise HTTPException(409, f"Request is already {lr.status.value}")
    lr.status = LeaveStatus(data.decision)
    lr.reviewed_by, lr.reviewed_at, lr.review_note = user.id, datetime.now(timezone.utc), data.note
    audit.log(db, user, data.decision, "leave", lr.id, {"employee_id": lr.employee_id}, request)
    db.commit()
    if lr.status == LeaveStatus.approved:
        finalize(db, lr.start_date, min(lr.end_date, today_local()), [lr.employee_id])
    return _load(db, lid)


@router.post("/{lid}/cancel", response_model=LeaveOut)
def cancel_leave(lid: int, request: Request, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    lr = _load(db, lid)
    if not lr:
        raise HTTPException(404, "Leave request not found")
    me = access.my_employee(db, user)
    if user.role != Role.admin and (not me or me.id != lr.employee_id):
        raise HTTPException(403, "Not allowed")
    if lr.status != LeaveStatus.pending:
        raise HTTPException(409, "Only pending requests can be cancelled")
    lr.status = LeaveStatus.cancelled
    audit.log(db, user, "cancel", "leave", lr.id, request=request)
    db.commit()
    return lr
