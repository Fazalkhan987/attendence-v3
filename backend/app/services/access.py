from fastapi import HTTPException
from sqlalchemy import false, or_, select, true
from sqlalchemy.orm import Session

from app.models import Department, Employee, Role, User


def my_employee(db: Session, user: User) -> Employee | None:
    return db.scalar(select(Employee).where(Employee.user_id == user.id))


def scope_clause(db: Session, user: User):
    """SQL clause restricting Employee rows to those the user may see (department-level RBAC)."""
    if user.role == Role.admin:
        return true()
    me = my_employee(db, user)
    mid = me.id if me else None
    if user.role == Role.employee:
        return Employee.id == (mid if mid else -1)
    if not mid:
        return false()
    dept_ids = db.scalars(select(Department.id).where(Department.head_id == mid)).all()
    conds = [Employee.supervisor_id == mid, Employee.id == mid]
    if dept_ids:
        conds.append(Employee.department_id.in_(dept_ids))
    return or_(*conds)


def assert_access(db: Session, user: User, employee_id: int) -> None:
    ok = db.scalar(select(Employee.id).where(Employee.id == employee_id, scope_clause(db, user)))
    if not ok:
        raise HTTPException(403, "You do not have access to this employee")
