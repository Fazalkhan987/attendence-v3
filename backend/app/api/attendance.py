from datetime import date, datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.core.deps import admin_only, get_current_user, staff_only
from app.database import get_db
from app.models import (Attendance, AttendanceCorrection, AttendanceStatus, Employee, Schedule,
                        User)
from app.schemas import AttendanceOut, AttendanceUpdate, CorrectionOut, ManualAttendanceIn
from app.services import access, audit
from app.services.attendance_service import _worked, finalize
from app.services.queries import attendance_query
from app.utils.timeutil import today_local

router = APIRouter(prefix="/attendance", tags=["attendance"])


def _snapshot(a: Attendance) -> dict:
    return {"check_in": a.check_in.isoformat() if a.check_in else None,
            "check_out": a.check_out.isoformat() if a.check_out else None,
            "status": a.status.value, "worked_minutes": a.worked_minutes}


def _load(db, aid):
    return db.scalar(select(Attendance).options(joinedload(Attendance.employee), joinedload(Attendance.schedule))
                     .where(Attendance.id == aid))


@router.get("", response_model=list[AttendanceOut])
def list_attendance(date_from: date | None = None, date_to: date | None = None, employee_id: int | None = None,
                    department_id: int | None = None, status: AttendanceStatus | None = None,
                    schedule_id: int | None = None, limit: int = 500, offset: int = 0,
                    db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    date_to = date_to or today_local()
    date_from = date_from or date_to - timedelta(days=30)
    if (date_to - date_from).days > 366:
        raise HTTPException(400, "Date range too large (max 366 days)")
    q = attendance_query(db, user, date_from, date_to, employee_id, department_id, status, schedule_id)
    return db.scalars(q.limit(min(limit, 2000)).offset(offset)).all()


@router.patch("/{aid}", response_model=AttendanceOut)
def correct_attendance(aid: int, data: AttendanceUpdate, request: Request, db: Session = Depends(get_db),
                       user: User = Depends(staff_only)):
    a = _load(db, aid)
    if not a:
        raise HTTPException(404, "Attendance record not found")
    access.assert_access(db, user, a.employee_id)
    before = _snapshot(a)
    fields = data.model_fields_set - {"reason"}
    if not fields:
        raise HTTPException(400, "Nothing to change")
    if "check_in" in fields:
        a.check_in = data.check_in
        a.check_in_camera_id = None
    if "check_out" in fields:
        a.check_out = data.check_out
        a.check_out_camera_id = None
    if "status" in fields and data.status:
        a.status = data.status
    if a.check_in and a.check_out and a.check_out < a.check_in:
        raise HTTPException(400, "Check-out cannot be before check-in")
    a.worked_minutes = _worked(a.check_in, a.check_out)
    a.source = "manual"
    db.add(AttendanceCorrection(attendance_id=a.id, employee_id=a.employee_id, previous=before,
                                updated=_snapshot(a), changed_by=user.id, reason=data.reason))
    audit.log(db, user, "correct", "attendance", a.id, {"reason": data.reason}, request)
    db.commit()
    return _load(db, aid)


@router.post("/manual", response_model=AttendanceOut, status_code=201)
def manual_attendance(data: ManualAttendanceIn, request: Request, db: Session = Depends(get_db),
                      user: User = Depends(staff_only)):
    access.assert_access(db, user, data.employee_id)
    if not db.get(Schedule, data.schedule_id):
        raise HTTPException(400, "Schedule not found")
    if data.check_in and data.check_out and data.check_out < data.check_in:
        raise HTTPException(400, "Check-out cannot be before check-in")
    if db.scalar(select(Attendance.id).where(
            Attendance.employee_id == data.employee_id, Attendance.schedule_id == data.schedule_id,
            Attendance.work_date == data.work_date)):
        raise HTTPException(409, "A record already exists for this session; edit it instead")
    a = Attendance(employee_id=data.employee_id, schedule_id=data.schedule_id, work_date=data.work_date,
                   status=data.status, check_in=data.check_in, check_out=data.check_out,
                   worked_minutes=_worked(data.check_in, data.check_out), source="manual",
                   remarks=data.reason)
    db.add(a)
    db.flush()
    db.add(AttendanceCorrection(attendance_id=a.id, employee_id=a.employee_id, previous={},
                                updated=_snapshot(a), changed_by=user.id, reason=data.reason))
    audit.log(db, user, "manual_create", "attendance", a.id, {"reason": data.reason}, request)
    db.commit()
    return _load(db, a.id)


@router.get("/{aid}/corrections", response_model=list[CorrectionOut])
def corrections(aid: int, db: Session = Depends(get_db), user: User = Depends(staff_only)):
    a = db.get(Attendance, aid)
    if not a:
        raise HTTPException(404, "Attendance record not found")
    access.assert_access(db, user, a.employee_id)
    return db.scalars(select(AttendanceCorrection).options(joinedload(AttendanceCorrection.user))
                      .where(AttendanceCorrection.attendance_id == aid)
                      .order_by(AttendanceCorrection.changed_at.desc())).all()


@router.post("/finalize")
def run_finalize(date_from: date | None = None, date_to: date | None = None, db: Session = Depends(get_db),
                 admin: User = Depends(admin_only)):
    today = today_local()
    return finalize(db, date_from or today, date_to or today)
