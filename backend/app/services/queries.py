from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.models import Attendance, AttendanceStatus, Employee, User
from app.services.access import scope_clause


def attendance_query(db: Session, user: User, date_from: date, date_to: date,
                     employee_id: int | None = None, department_id: int | None = None,
                     status: AttendanceStatus | None = None, schedule_id: int | None = None):
    q = (select(Attendance).join(Employee, Employee.id == Attendance.employee_id)
         .options(joinedload(Attendance.employee), joinedload(Attendance.schedule))
         .where(scope_clause(db, user), Attendance.work_date >= date_from, Attendance.work_date <= date_to))
    if employee_id:
        q = q.where(Attendance.employee_id == employee_id)
    if department_id:
        q = q.where(Employee.department_id == department_id)
    if status:
        q = q.where(Attendance.status == status)
    if schedule_id:
        q = q.where(Attendance.schedule_id == schedule_id)
    return q.order_by(Attendance.work_date.desc(), Employee.employee_code)
