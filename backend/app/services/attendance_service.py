"""Attendance rules. The backend is the only component allowed to create attendance."""
import hashlib
import logging
from datetime import date, datetime, timedelta, timezone

from fastapi import HTTPException
from sqlalchemy import delete, or_, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.database import SessionLocal
from app.models import (Attendance, AttendanceStatus, Camera, CameraType, Decision, Employee,
                        EmploymentStatus, LeaveRequest, LeaveStatus, RecognitionEvent, Schedule,
                        ScheduleAssignment)
from app.schemas import RecognitionEventIn
from app.utils.timeutil import TZ, combine_local, now_local, to_local, today_local

log = logging.getLogger("attendance")


def sessions_for(db: Session, employee_id: int, d: date) -> list[Schedule]:
    rows = db.scalars(
        select(Schedule).join(ScheduleAssignment, ScheduleAssignment.schedule_id == Schedule.id)
        .where(ScheduleAssignment.employee_id == employee_id, Schedule.is_active.is_(True),
               ScheduleAssignment.effective_from <= d,
               or_(ScheduleAssignment.effective_to.is_(None), ScheduleAssignment.effective_to >= d))
        .order_by(Schedule.start_time)).all()
    return [s for s in {s.id: s for s in rows}.values() if d.weekday() in s.working_days]


def _worked(check_in: datetime | None, check_out: datetime | None) -> int | None:
    if check_in and check_out:
        return max(0, int((check_out - check_in).total_seconds() // 60))
    return None


def process_event(db: Session, camera: Camera, p: RecognitionEventIn) -> RecognitionEvent:
    ts = p.timestamp if p.timestamp.tzinfo else p.timestamp.replace(tzinfo=TZ)
    ts_utc = ts.astimezone(timezone.utc)
    key = p.event_id or hashlib.sha256(
        f"{p.employee_id}|{camera.camera_code}|{ts_utc.isoformat()}".encode()).hexdigest()[:48]

    if db.scalar(select(RecognitionEvent.id).where(
            RecognitionEvent.camera_id == camera.id, RecognitionEvent.event_uuid == key)):
        raise HTTPException(409, "Replayed event")

    ev = RecognitionEvent(event_uuid=key, camera_id=camera.id, employee_code=p.employee_id,
                          confidence=p.confidence, event_time=ts_utc, decision=Decision.rejected)

    def finish(decision: Decision, reason: str, action: str | None = None, att: Attendance | None = None):
        ev.decision, ev.reason, ev.action = decision, reason, action
        ev.attendance_id = att.id if att else None
        db.add(ev)
        try:
            db.commit()
        except IntegrityError:
            db.rollback()
            raise HTTPException(409, "Replayed event")
        return ev

    if abs((datetime.now(timezone.utc) - ts_utc).total_seconds()) > settings.EVENT_MAX_SKEW_SECONDS:
        return finish(Decision.rejected, "stale_or_future_timestamp")
    if p.confidence < settings.RECOGNITION_MIN_CONFIDENCE:
        return finish(Decision.rejected, "low_confidence")

    emp = db.scalar(select(Employee).where(Employee.employee_code == p.employee_id))
    if not emp:
        return finish(Decision.rejected, "unknown_employee")
    ev.employee_id = emp.id
    if emp.status != EmploymentStatus.active or (emp.user and not emp.user.is_active):
        return finish(Decision.rejected, "employee_inactive")
    if camera.department_id and camera.department_id != emp.department_id:
        return finish(Decision.rejected, "camera_department_mismatch")

    # serialise concurrent events for the same employee
    db.execute(select(Employee.id).where(Employee.id == emp.id).with_for_update())

    window_start = ts_utc - timedelta(seconds=settings.DUPLICATE_WINDOW_SECONDS)
    if db.scalar(select(RecognitionEvent.id).where(
            RecognitionEvent.employee_id == emp.id, RecognitionEvent.camera_id == camera.id,
            RecognitionEvent.decision == Decision.accepted,
            RecognitionEvent.event_time >= window_start, RecognitionEvent.event_time <= ts_utc).limit(1)):
        return finish(Decision.ignored, "duplicate_event")

    local = ts.astimezone(TZ)
    d = local.date()
    if db.scalar(select(LeaveRequest.id).where(
            LeaveRequest.employee_id == emp.id, LeaveRequest.status == LeaveStatus.approved,
            LeaveRequest.start_date <= d, LeaveRequest.end_date >= d).limit(1)):
        return finish(Decision.rejected, "on_approved_leave")

    sessions = sessions_for(db, emp.id, d)
    if not sessions:
        return finish(Decision.rejected, "no_schedule_today")

    existing = {a.schedule_id: a for a in db.scalars(
        select(Attendance).where(Attendance.employee_id == emp.id, Attendance.work_date == d))}
    can_in = camera.camera_type in (CameraType.entry, CameraType.both)
    can_out = camera.camera_type in (CameraType.exit, CameraType.both)

    for s in sessions:
        start, end = combine_local(d, s.start_time), combine_local(d, s.end_time)
        att = existing.get(s.id)

        if att is None:
            opens = start - timedelta(minutes=s.checkin_early_minutes)
            if can_in and s.camera_id in (None, camera.id) and opens <= local <= end:
                late = local > start + timedelta(minutes=s.grace_minutes)
                att = Attendance(employee_id=emp.id, schedule_id=s.id, work_date=d, check_in=ts_utc,
                                 check_in_camera_id=camera.id, source="recognition",
                                 status=AttendanceStatus.late if late else AttendanceStatus.present)
                db.add(att)
                db.flush()
                return finish(Decision.accepted, "check_in_recorded", "check_in", att)

        elif att.check_in and not att.check_out:
            opens = end - timedelta(minutes=s.checkout_before_minutes)
            closes = end + timedelta(minutes=s.checkout_after_minutes)
            earliest = to_local(att.check_in) + timedelta(minutes=settings.MIN_STAY_MINUTES)
            if can_out and opens <= local <= closes and local >= earliest:
                att.check_out, att.check_out_camera_id = ts_utc, camera.id
                att.worked_minutes = _worked(att.check_in, ts_utc)
                att.is_early_departure = local < end
                if att.status == AttendanceStatus.incomplete:
                    late = to_local(att.check_in) > start + timedelta(minutes=s.grace_minutes)
                    att.status = AttendanceStatus.late if late else AttendanceStatus.present
                if att.worked_minutes < 0.5 * (end - start).total_seconds() / 60:
                    att.status = AttendanceStatus.half_day
                return finish(Decision.accepted, "check_out_recorded", "check_out", att)

    return finish(Decision.ignored, "no_action_window_or_already_recorded")


def finalize(db: Session, date_from: date, date_to: date, employee_ids: list[int] | None = None) -> dict:
    """Create Absent / On Leave rows and close open sessions once the verification period has passed."""
    now = now_local()
    created = closed = 0
    leaves_q = select(LeaveRequest).where(
        LeaveRequest.status == LeaveStatus.approved,
        LeaveRequest.start_date <= date_to, LeaveRequest.end_date >= date_from)
    if employee_ids:
        leaves_q = leaves_q.where(LeaveRequest.employee_id.in_(employee_ids))
    leaves = db.scalars(leaves_q).all()

    d = date_from
    while d <= min(date_to, now.date()):
        q = (select(Employee, Schedule).join(ScheduleAssignment, ScheduleAssignment.employee_id == Employee.id)
             .join(Schedule, Schedule.id == ScheduleAssignment.schedule_id)
             .where(Employee.status == EmploymentStatus.active, Schedule.is_active.is_(True),
                    ScheduleAssignment.effective_from <= d,
                    or_(ScheduleAssignment.effective_to.is_(None), ScheduleAssignment.effective_to >= d)))
        if employee_ids:
            q = q.where(Employee.id.in_(employee_ids))
        pairs = {(e.id, s.id): (e, s) for e, s in db.execute(q).all() if d.weekday() in s.working_days}
        att_rows = {(a.employee_id, a.schedule_id): a for a in db.scalars(
            select(Attendance).where(Attendance.work_date == d))}
        on_leave = {l.employee_id for l in leaves if l.start_date <= d <= l.end_date}

        for (eid, sid), (emp, s) in pairs.items():
            deadline = combine_local(d, s.end_time) + timedelta(minutes=settings.ABSENT_VERIFICATION_MINUTES)
            if now < deadline:
                continue
            att = att_rows.get((eid, sid))
            if att is None:
                db.execute(pg_insert(Attendance).values(
                    employee_id=eid, schedule_id=sid, work_date=d, source="system",
                    status=AttendanceStatus.on_leave if eid in on_leave else AttendanceStatus.absent)
                    .on_conflict_do_nothing(constraint="uq_attendance_session"))
                created += 1
            elif att.source == "system" and att.status == AttendanceStatus.absent and eid in on_leave:
                att.status = AttendanceStatus.on_leave
            elif (att.source == "recognition" and att.check_in and not att.check_out
                  and att.status in (AttendanceStatus.present, AttendanceStatus.late)):
                att.status = AttendanceStatus.incomplete
                closed += 1
        d += timedelta(days=1)
    db.commit()
    return {"created": created, "closed": closed}


def run_finalize_job() -> None:
    with SessionLocal() as db:
        today = today_local()
        finalize(db, today - timedelta(days=2), today)
        cutoff = datetime.now(timezone.utc) - timedelta(days=settings.EVENT_RETENTION_DAYS)
        db.execute(delete(RecognitionEvent).where(RecognitionEvent.event_time < cutoff))
        db.commit()
