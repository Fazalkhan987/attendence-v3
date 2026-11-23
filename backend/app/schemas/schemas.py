from datetime import date, datetime, time
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator, model_validator

from app.models import (AttendanceStatus, CameraType, Decision, EmploymentStatus,
                        LeaveStatus, Role)


class ORM(BaseModel):
    model_config = ConfigDict(from_attributes=True)


def _lower(v: str) -> str:
    return v.strip().lower()


# ---------- auth ----------
class LoginIn(BaseModel):
    email: str
    password: str


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: Role


class ChangePasswordIn(BaseModel):
    current_password: str
    new_password: str = Field(min_length=8, max_length=72)


class UserOut(ORM):
    id: int
    email: str
    role: Role
    is_active: bool


# ---------- departments ----------
class DepartmentIn(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    code: str = Field(min_length=2, max_length=20)
    description: Optional[str] = None
    head_id: Optional[int] = None
    is_active: bool = True


class DepartmentUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=120)
    code: Optional[str] = Field(None, min_length=2, max_length=20)
    description: Optional[str] = None
    head_id: Optional[int] = None
    is_active: Optional[bool] = None


class DepartmentOut(ORM):
    id: int
    name: str
    code: str
    description: Optional[str]
    head_id: Optional[int]
    is_active: bool


# ---------- employees ----------
class AccountIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=72)
    role: Role = Role.employee
    is_active: bool = True

    @field_validator("email")
    @classmethod
    def _email_lower(cls, v):
        return _lower(v)


class AccountUpdate(BaseModel):
    email: Optional[EmailStr] = None
    password: Optional[str] = Field(None, min_length=8, max_length=72)
    role: Optional[Role] = None
    is_active: Optional[bool] = None


class EmployeeBase(BaseModel):
    employee_code: str = Field(min_length=2, max_length=30, pattern=r"^[A-Za-z0-9._-]+$")
    full_name: str = Field(min_length=2, max_length=150)
    email: EmailStr
    phone: Optional[str] = Field(None, max_length=30)
    address: Optional[str] = None
    photo: Optional[str] = Field(None, max_length=700_000)
    department_id: int
    designation: str = Field(min_length=2, max_length=100)
    joining_date: date
    status: EmploymentStatus = EmploymentStatus.active
    supervisor_id: Optional[int] = None

    @field_validator("email")
    @classmethod
    def _email_lower(cls, v):
        return _lower(v)


class EmployeeCreate(EmployeeBase):
    face_consent: bool = False
    account: Optional[AccountIn] = None


class EmployeeUpdate(BaseModel):
    full_name: Optional[str] = Field(None, min_length=2, max_length=150)
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    photo: Optional[str] = Field(None, max_length=700_000)
    department_id: Optional[int] = None
    designation: Optional[str] = None
    joining_date: Optional[date] = None
    status: Optional[EmploymentStatus] = None
    supervisor_id: Optional[int] = None
    face_consent: Optional[bool] = None
    account: Optional[AccountUpdate] = None


class EmployeeOut(ORM):
    id: int
    employee_code: str
    full_name: str
    email: str
    phone: Optional[str]
    address: Optional[str]
    photo: Optional[str]
    department_id: int
    department_name: Optional[str]
    designation: str
    joining_date: date
    status: EmploymentStatus
    supervisor_id: Optional[int]
    supervisor_name: Optional[str]
    face_consent: bool
    face_samples: int
    user_id: Optional[int]
    account_role: Optional[Role]
    account_active: Optional[bool]


class MeOut(BaseModel):
    user: UserOut
    employee: Optional[EmployeeOut]


# ---------- faces ----------
class EnrollIn(BaseModel):
    images: list[str] = Field(min_length=3, max_length=20)


class EnrollOut(BaseModel):
    employee_id: int
    samples_stored: int
    rejected: list[str]


# ---------- cameras ----------
class CameraIn(BaseModel):
    camera_code: str = Field(min_length=2, max_length=30, pattern=r"^[A-Za-z0-9._-]+$")
    name: str = Field(min_length=2, max_length=100)
    location: Optional[str] = None
    department_id: Optional[int] = None
    camera_type: CameraType = CameraType.both
    stream_url: Optional[str] = None
    is_active: bool = True


class CameraUpdate(BaseModel):
    name: Optional[str] = None
    location: Optional[str] = None
    department_id: Optional[int] = None
    camera_type: Optional[CameraType] = None
    stream_url: Optional[str] = None
    is_active: Optional[bool] = None


class CameraOut(ORM):
    id: int
    camera_code: str
    name: str
    location: Optional[str]
    department_id: Optional[int]
    camera_type: CameraType
    stream_url: Optional[str]
    is_active: bool


class CameraSecretOut(CameraOut):
    secret: str


# ---------- schedules ----------
class ScheduleIn(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    department_id: int
    camera_id: Optional[int] = None
    start_time: time
    end_time: time
    working_days: list[int] = Field(min_length=1)
    grace_minutes: int = Field(20, ge=0, le=240)
    checkin_early_minutes: int = Field(60, ge=0, le=480)
    checkout_before_minutes: int = Field(30, ge=0, le=240)
    checkout_after_minutes: int = Field(60, ge=0, le=480)
    is_active: bool = True

    @field_validator("working_days")
    @classmethod
    def _days(cls, v):
        if any(d < 0 or d > 6 for d in v):
            raise ValueError("working_days must be 0 (Mon) to 6 (Sun)")
        return sorted(set(v))

    @model_validator(mode="after")
    def _times(self):
        if self.end_time <= self.start_time:
            raise ValueError("end_time must be after start_time")
        return self


class ScheduleUpdate(BaseModel):
    name: Optional[str] = None
    department_id: Optional[int] = None
    camera_id: Optional[int] = None
    start_time: Optional[time] = None
    end_time: Optional[time] = None
    working_days: Optional[list[int]] = None
    grace_minutes: Optional[int] = Field(None, ge=0, le=240)
    checkin_early_minutes: Optional[int] = Field(None, ge=0, le=480)
    checkout_before_minutes: Optional[int] = Field(None, ge=0, le=240)
    checkout_after_minutes: Optional[int] = Field(None, ge=0, le=480)
    is_active: Optional[bool] = None


class ScheduleOut(ORM):
    id: int
    name: str
    department_id: int
    department_name: Optional[str]
    camera_id: Optional[int]
    camera_code: Optional[str]
    start_time: time
    end_time: time
    working_days: list[int]
    grace_minutes: int
    checkin_early_minutes: int
    checkout_before_minutes: int
    checkout_after_minutes: int
    is_active: bool


class AssignmentIn(BaseModel):
    employee_ids: list[int] = Field(min_length=1)
    effective_from: date = Field(default_factory=date.today)
    effective_to: Optional[date] = None


class AssignmentOut(ORM):
    id: int
    schedule_id: int
    employee_id: int
    employee_name: str
    employee_code: str
    effective_from: date
    effective_to: Optional[date]


# ---------- leave ----------
class LeaveTypeIn(BaseModel):
    name: str = Field(min_length=2, max_length=60)


class LeaveTypeOut(ORM):
    id: int
    name: str
    is_active: bool


class LeaveIn(BaseModel):
    leave_type_id: int
    start_date: date
    end_date: date
    reason: Optional[str] = Field(None, max_length=1000)
    employee_id: Optional[int] = None  # admin only

    @model_validator(mode="after")
    def _dates(self):
        if self.end_date < self.start_date:
            raise ValueError("end_date must be on or after start_date")
        if (self.end_date - self.start_date).days > 60:
            raise ValueError("A single leave request cannot exceed 61 days")
        return self


class LeaveReviewIn(BaseModel):
    decision: Literal["approved", "rejected"]
    note: Optional[str] = Field(None, max_length=500)


class LeaveOut(ORM):
    id: int
    employee_id: int
    employee_name: str
    employee_code: str
    leave_type_id: int
    leave_type_name: str
    start_date: date
    end_date: date
    reason: Optional[str]
    status: LeaveStatus
    reviewed_at: Optional[datetime]
    review_note: Optional[str]
    created_at: datetime


# ---------- attendance ----------
class AttendanceOut(ORM):
    id: int
    employee_id: int
    employee_code: str
    employee_name: str
    schedule_id: int
    schedule_name: str
    schedule_start: time
    schedule_end: time
    work_date: date
    check_in: Optional[datetime]
    check_out: Optional[datetime]
    status: AttendanceStatus
    worked_minutes: Optional[int]
    is_early_departure: bool
    source: str
    remarks: Optional[str]


class AttendanceUpdate(BaseModel):
    check_in: Optional[datetime] = None
    check_out: Optional[datetime] = None
    status: Optional[AttendanceStatus] = None
    reason: str = Field(min_length=3, max_length=500)


class ManualAttendanceIn(BaseModel):
    employee_id: int
    schedule_id: int
    work_date: date
    status: AttendanceStatus
    check_in: Optional[datetime] = None
    check_out: Optional[datetime] = None
    reason: str = Field(min_length=3, max_length=500)


class CorrectionOut(ORM):
    id: int
    attendance_id: int
    employee_id: int
    previous: dict
    updated: dict
    changed_by: Optional[int]
    changed_by_email: Optional[str]
    changed_at: datetime
    reason: str


# ---------- recognition ----------
class RecognitionEventIn(BaseModel):
    event_id: Optional[str] = Field(None, max_length=64)
    employee_id: str = Field(min_length=1, max_length=30)
    camera_id: str = Field(min_length=1, max_length=30)
    confidence: float = Field(ge=0, le=1)
    timestamp: datetime


class RecognitionEventOut(ORM):
    id: int
    employee_code: str
    employee_name: Optional[str]
    camera_code: Optional[str]
    confidence: float
    event_time: datetime
    received_at: datetime
    decision: Decision
    reason: Optional[str]
    action: Optional[str]
    attendance_id: Optional[int]


class AuditOut(ORM):
    id: int
    user_email: Optional[str]
    action: str
    entity: str
    entity_id: Optional[str]
    details: Optional[dict]
    ip: Optional[str]
    created_at: datetime
