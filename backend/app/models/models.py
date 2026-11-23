import enum
from datetime import date, datetime, time
from typing import Optional

from sqlalchemy import (JSON, Boolean, CheckConstraint, Date, DateTime, Enum, Float,
                        ForeignKey, Index, Integer, LargeBinary, String, Text, Time,
                        UniqueConstraint, func, select)
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import Mapped, column_property, mapped_column, relationship

from app.database import Base


class Role(str, enum.Enum):
    admin = "admin"
    supervisor = "supervisor"
    employee = "employee"


class EmploymentStatus(str, enum.Enum):
    active = "active"
    inactive = "inactive"
    suspended = "suspended"
    terminated = "terminated"


class CameraType(str, enum.Enum):
    entry = "entry"
    exit = "exit"
    both = "both"


class AttendanceStatus(str, enum.Enum):
    present = "present"
    late = "late"
    absent = "absent"
    on_leave = "on_leave"
    half_day = "half_day"
    incomplete = "incomplete"
    excused = "excused"


class LeaveStatus(str, enum.Enum):
    pending = "pending"
    approved = "approved"
    rejected = "rejected"
    cancelled = "cancelled"


class Decision(str, enum.Enum):
    accepted = "accepted"
    ignored = "ignored"
    rejected = "rejected"


def _enum(e):
    return Enum(e, native_enum=False, length=20, values_callable=lambda x: [i.value for i in x])


def _ts():
    return mapped_column(DateTime(timezone=True), server_default=func.now())


class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[Role] = mapped_column(_enum(Role), default=Role.employee)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = _ts()
    last_login: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    employee: Mapped[Optional["Employee"]] = relationship(back_populates="user", uselist=False)


class Department(Base):
    __tablename__ = "departments"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120), unique=True)
    code: Mapped[str] = mapped_column(String(20), unique=True)
    description: Mapped[Optional[str]] = mapped_column(Text)
    head_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("employees.id", use_alter=True, name="fk_department_head", ondelete="SET NULL"))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = _ts()


class Employee(Base):
    __tablename__ = "employees"
    id: Mapped[int] = mapped_column(primary_key=True)
    employee_code: Mapped[str] = mapped_column(String(30), unique=True, index=True)
    user_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), unique=True)
    full_name: Mapped[str] = mapped_column(String(150))
    email: Mapped[str] = mapped_column(String(255), unique=True)
    phone: Mapped[Optional[str]] = mapped_column(String(30))
    address: Mapped[Optional[str]] = mapped_column(Text)
    photo: Mapped[Optional[str]] = mapped_column(Text)
    department_id: Mapped[int] = mapped_column(ForeignKey("departments.id"), index=True)
    designation: Mapped[str] = mapped_column(String(100))
    joining_date: Mapped[date] = mapped_column(Date)
    status: Mapped[EmploymentStatus] = mapped_column(_enum(EmploymentStatus), default=EmploymentStatus.active)
    supervisor_id: Mapped[Optional[int]] = mapped_column(ForeignKey("employees.id", ondelete="SET NULL"))
    face_consent: Mapped[bool] = mapped_column(Boolean, default=False)
    face_consent_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = _ts()

    user: Mapped[Optional[User]] = relationship(back_populates="employee")
    department: Mapped[Department] = relationship(foreign_keys=[department_id])
    supervisor: Mapped[Optional["Employee"]] = relationship(remote_side=[id], foreign_keys=[supervisor_id])

    @property
    def department_name(self): return self.department.name if self.department else None
    @property
    def supervisor_name(self): return self.supervisor.full_name if self.supervisor else None
    @property
    def account_role(self): return self.user.role if self.user else None
    @property
    def account_active(self): return self.user.is_active if self.user else None


class FaceEmbedding(Base):
    __tablename__ = "face_embeddings"
    id: Mapped[int] = mapped_column(primary_key=True)
    employee_id: Mapped[int] = mapped_column(ForeignKey("employees.id", ondelete="CASCADE"), index=True)
    embedding_enc: Mapped[bytes] = mapped_column(LargeBinary)  # Fernet-encrypted float32[512]
    quality: Mapped[float] = mapped_column(Float, default=0)
    created_at: Mapped[datetime] = _ts()


Employee.face_samples = column_property(
    select(func.count(FaceEmbedding.id)).where(FaceEmbedding.employee_id == Employee.id)
    .correlate_except(FaceEmbedding).scalar_subquery())


class Camera(Base):
    __tablename__ = "cameras"
    id: Mapped[int] = mapped_column(primary_key=True)
    camera_code: Mapped[str] = mapped_column(String(30), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(100))
    location: Mapped[Optional[str]] = mapped_column(String(150))
    department_id: Mapped[Optional[int]] = mapped_column(ForeignKey("departments.id", ondelete="SET NULL"))
    camera_type: Mapped[CameraType] = mapped_column(_enum(CameraType), default=CameraType.both)
    stream_url: Mapped[Optional[str]] = mapped_column(String(255))
    secret_enc: Mapped[bytes] = mapped_column(LargeBinary)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = _ts()


class LeaveType(Base):
    __tablename__ = "leave_types"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(60), unique=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class Schedule(Base):
    """One schedule == one working session. Several schedules per employee => several sessions per day."""
    __tablename__ = "schedules"
    __table_args__ = (CheckConstraint("end_time > start_time", name="ck_schedule_time"),
                      CheckConstraint("grace_minutes >= 0", name="ck_schedule_grace"))
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    department_id: Mapped[int] = mapped_column(ForeignKey("departments.id"), index=True)
    camera_id: Mapped[Optional[int]] = mapped_column(ForeignKey("cameras.id", ondelete="SET NULL"))
    start_time: Mapped[time] = mapped_column(Time)
    end_time: Mapped[time] = mapped_column(Time)
    working_days: Mapped[list[int]] = mapped_column(ARRAY(Integer))  # 0=Mon .. 6=Sun
    grace_minutes: Mapped[int] = mapped_column(Integer, default=20)
    checkin_early_minutes: Mapped[int] = mapped_column(Integer, default=60)
    checkout_before_minutes: Mapped[int] = mapped_column(Integer, default=30)
    checkout_after_minutes: Mapped[int] = mapped_column(Integer, default=60)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = _ts()

    department: Mapped[Department] = relationship()
    camera: Mapped[Optional[Camera]] = relationship()

    @property
    def department_name(self): return self.department.name if self.department else None
    @property
    def camera_code(self): return self.camera.camera_code if self.camera else None


class ScheduleAssignment(Base):
    __tablename__ = "schedule_assignments"
    __table_args__ = (UniqueConstraint("schedule_id", "employee_id", "effective_from", name="uq_assignment"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    schedule_id: Mapped[int] = mapped_column(ForeignKey("schedules.id", ondelete="CASCADE"), index=True)
    employee_id: Mapped[int] = mapped_column(ForeignKey("employees.id", ondelete="CASCADE"), index=True)
    effective_from: Mapped[date] = mapped_column(Date)
    effective_to: Mapped[Optional[date]] = mapped_column(Date)
    created_at: Mapped[datetime] = _ts()
    employee: Mapped[Employee] = relationship()
    schedule: Mapped[Schedule] = relationship()

    @property
    def employee_name(self): return self.employee.full_name
    @property
    def employee_code(self): return self.employee.employee_code


class RecognitionEvent(Base):
    __tablename__ = "recognition_events"
    __table_args__ = (UniqueConstraint("camera_id", "event_uuid", name="uq_event_camera_uuid"),
                      Index("ix_event_emp_time", "employee_id", "event_time"))
    id: Mapped[int] = mapped_column(primary_key=True)
    event_uuid: Mapped[str] = mapped_column(String(64))
    employee_code: Mapped[str] = mapped_column(String(30))
    employee_id: Mapped[Optional[int]] = mapped_column(ForeignKey("employees.id", ondelete="SET NULL"))
    camera_id: Mapped[int] = mapped_column(ForeignKey("cameras.id"))
    confidence: Mapped[float] = mapped_column(Float)
    event_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    received_at: Mapped[datetime] = _ts()
    decision: Mapped[Decision] = mapped_column(_enum(Decision))
    reason: Mapped[Optional[str]] = mapped_column(String(60))
    action: Mapped[Optional[str]] = mapped_column(String(20))
    attendance_id: Mapped[Optional[int]] = mapped_column(ForeignKey("attendance.id", ondelete="SET NULL"))
    camera: Mapped[Camera] = relationship()
    employee: Mapped[Optional[Employee]] = relationship()

    @property
    def camera_code(self): return self.camera.camera_code if self.camera else None
    @property
    def employee_name(self): return self.employee.full_name if self.employee else None


class Attendance(Base):
    __tablename__ = "attendance"
    __table_args__ = (UniqueConstraint("employee_id", "schedule_id", "work_date", name="uq_attendance_session"),
                      Index("ix_attendance_date", "work_date"),
                      Index("ix_attendance_emp_date", "employee_id", "work_date"))
    id: Mapped[int] = mapped_column(primary_key=True)
    employee_id: Mapped[int] = mapped_column(ForeignKey("employees.id", ondelete="CASCADE"))
    schedule_id: Mapped[int] = mapped_column(ForeignKey("schedules.id", ondelete="CASCADE"))
    work_date: Mapped[date] = mapped_column(Date)
    check_in: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    check_out: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    status: Mapped[AttendanceStatus] = mapped_column(_enum(AttendanceStatus))
    check_in_camera_id: Mapped[Optional[int]] = mapped_column(ForeignKey("cameras.id", ondelete="SET NULL"))
    check_out_camera_id: Mapped[Optional[int]] = mapped_column(ForeignKey("cameras.id", ondelete="SET NULL"))
    worked_minutes: Mapped[Optional[int]] = mapped_column(Integer)
    is_early_departure: Mapped[bool] = mapped_column(Boolean, default=False)
    source: Mapped[str] = mapped_column(String(20), default="recognition")  # recognition | system | manual
    remarks: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = _ts()
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    employee: Mapped[Employee] = relationship()
    schedule: Mapped[Schedule] = relationship()

    @property
    def employee_code(self): return self.employee.employee_code
    @property
    def employee_name(self): return self.employee.full_name
    @property
    def schedule_name(self): return self.schedule.name
    @property
    def schedule_start(self): return self.schedule.start_time
    @property
    def schedule_end(self): return self.schedule.end_time


class LeaveRequest(Base):
    __tablename__ = "leave_requests"
    __table_args__ = (CheckConstraint("end_date >= start_date", name="ck_leave_dates"),
                      Index("ix_leave_emp_dates", "employee_id", "start_date", "end_date"))
    id: Mapped[int] = mapped_column(primary_key=True)
    employee_id: Mapped[int] = mapped_column(ForeignKey("employees.id", ondelete="CASCADE"))
    leave_type_id: Mapped[int] = mapped_column(ForeignKey("leave_types.id"))
    start_date: Mapped[date] = mapped_column(Date)
    end_date: Mapped[date] = mapped_column(Date)
    reason: Mapped[Optional[str]] = mapped_column(Text)
    status: Mapped[LeaveStatus] = mapped_column(_enum(LeaveStatus), default=LeaveStatus.pending)
    reviewed_by: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    reviewed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    review_note: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = _ts()
    employee: Mapped[Employee] = relationship()
    leave_type: Mapped[LeaveType] = relationship()

    @property
    def employee_name(self): return self.employee.full_name
    @property
    def employee_code(self): return self.employee.employee_code
    @property
    def leave_type_name(self): return self.leave_type.name


class AttendanceCorrection(Base):
    __tablename__ = "attendance_corrections"
    id: Mapped[int] = mapped_column(primary_key=True)
    attendance_id: Mapped[int] = mapped_column(ForeignKey("attendance.id", ondelete="CASCADE"), index=True)
    employee_id: Mapped[int] = mapped_column(ForeignKey("employees.id", ondelete="CASCADE"), index=True)
    previous: Mapped[dict] = mapped_column(JSON)
    updated: Mapped[dict] = mapped_column(JSON)
    changed_by: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    changed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    reason: Mapped[str] = mapped_column(Text)
    user: Mapped[Optional[User]] = relationship()

    @property
    def changed_by_email(self): return self.user.email if self.user else None


class AuditLog(Base):
    __tablename__ = "audit_logs"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    action: Mapped[str] = mapped_column(String(60), index=True)
    entity: Mapped[str] = mapped_column(String(60))
    entity_id: Mapped[Optional[str]] = mapped_column(String(100))
    details: Mapped[Optional[dict]] = mapped_column(JSON)
    ip: Mapped[Optional[str]] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)
    user: Mapped[Optional[User]] = relationship()

    @property
    def user_email(self): return self.user.email if self.user else None
