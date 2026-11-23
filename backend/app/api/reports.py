import csv
import io
from collections import defaultdict
from datetime import date, timedelta

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.deps import admin_only, staff_only
from app.database import get_db
from app.models import (Attendance, AttendanceStatus, Camera, Decision, Employee, EmploymentStatus,
                        LeaveRequest, LeaveStatus, RecognitionEvent, User)
from app.services import access
from app.services.queries import attendance_query
from app.utils.timeutil import TZ, today_local
from datetime import datetime

router = APIRouter(prefix="/reports", tags=["reports"])


@router.get("/dashboard")
def dashboard(db: Session = Depends(get_db), user: User = Depends(staff_only)):
    today = today_local()
    scope = access.scope_clause(db, user)
    counts = {s.value: 0 for s in AttendanceStatus}
    for st, n in db.execute(select(Attendance.status, func.count()).join(Employee, Employee.id == Attendance.employee_id)
                            .where(scope, Attendance.work_date == today).group_by(Attendance.status)).all():
        counts[st.value] = n
    start = datetime.combine(today, datetime.min.time(), tzinfo=TZ)
    return {
        "date": today,
        "employees": db.scalar(select(func.count(Employee.id)).where(scope, Employee.status == EmploymentStatus.active)),
        "attendance_today": counts,
        "pending_leave": db.scalar(select(func.count(LeaveRequest.id)).join(Employee, Employee.id == LeaveRequest.employee_id)
                                   .where(scope, LeaveRequest.status == LeaveStatus.pending)),
        "accepted_events_today": db.scalar(select(func.count(RecognitionEvent.id)).where(
            RecognitionEvent.decision == Decision.accepted, RecognitionEvent.event_time >= start)),
        "active_cameras": db.scalar(select(func.count(Camera.id)).where(Camera.is_active.is_(True))),
    }


@router.get("/summary")
def summary(date_from: date | None = None, date_to: date | None = None, department_id: int | None = None,
            db: Session = Depends(get_db), user: User = Depends(staff_only)):
    date_to = date_to or today_local()
    date_from = date_from or date_to.replace(day=1)
    rows = db.scalars(attendance_query(db, user, date_from, date_to, department_id=department_id)).all()
    agg: dict[int, dict] = {}
    for a in rows:
        e = agg.setdefault(a.employee_id, {"employee_id": a.employee_id, "employee_code": a.employee.employee_code,
                                           "employee_name": a.employee.full_name, "worked_minutes": 0,
                                           **{s.value: 0 for s in AttendanceStatus}})
        e[a.status.value] += 1
        e["worked_minutes"] += a.worked_minutes or 0
    return {"date_from": date_from, "date_to": date_to, "rows": sorted(agg.values(), key=lambda r: r["employee_code"])}


@router.get("/attendance.csv")
def export_csv(date_from: date | None = None, date_to: date | None = None, department_id: int | None = None,
               db: Session = Depends(get_db), user: User = Depends(staff_only)):
    date_to = date_to or today_local()
    date_from = date_from or date_to.replace(day=1)
    rows = db.scalars(attendance_query(db, user, date_from, date_to, department_id=department_id)).all()
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["date", "employee_id", "name", "session", "check_in", "check_out", "status", "worked_minutes",
                "early_departure", "source"])
    for a in rows:
        w.writerow([a.work_date, a.employee.employee_code, a.employee.full_name, a.schedule.name,
                    a.check_in.astimezone(TZ).strftime("%H:%M:%S") if a.check_in else "",
                    a.check_out.astimezone(TZ).strftime("%H:%M:%S") if a.check_out else "",
                    a.status.value, a.worked_minutes or "", a.is_early_departure, a.source])
    buf.seek(0)
    return StreamingResponse(iter([buf.getvalue()]), media_type="text/csv",
                             headers={"Content-Disposition": f"attachment; filename=attendance_{date_from}_{date_to}.csv"})


@router.get("/audit-logs")
def audit_logs(limit: int = 200, db: Session = Depends(get_db), _: User = Depends(admin_only)):
    from sqlalchemy.orm import joinedload
    from app.models import AuditLog
    from app.schemas import AuditOut
    rows = db.scalars(select(AuditLog).options(joinedload(AuditLog.user)).order_by(AuditLog.created_at.desc())
                      .limit(min(limit, 1000))).all()
    return [AuditOut.model_validate(r) for r in rows]
