from datetime import date, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.core.deps import authenticate_camera, staff_only
from app.database import get_db
from app.models import Camera, Decision, Employee, RecognitionEvent, Role, User
from app.schemas import RecognitionEventIn, RecognitionEventOut
from app.services import access
from app.services.attendance_service import process_event
from app.utils.timeutil import TZ, today_local

router = APIRouter(prefix="/recognition", tags=["recognition"])


@router.post("/events", response_model=RecognitionEventOut)
def receive_event(payload: RecognitionEventIn, camera: Camera = Depends(authenticate_camera),
                  db: Session = Depends(get_db)):
    if payload.camera_id != camera.camera_code:
        raise HTTPException(403, "camera_id does not match authenticated camera")
    ev = process_event(db, camera, payload)
    return RecognitionEventOut.model_validate(ev)


@router.get("/events", response_model=list[RecognitionEventOut])
def list_events(day: date | None = None, decision: Decision | None = None, limit: int = 200,
                db: Session = Depends(get_db), user: User = Depends(staff_only)):
    day = day or today_local()
    start = datetime.combine(day, datetime.min.time(), tzinfo=TZ)
    q = (select(RecognitionEvent).options(joinedload(RecognitionEvent.camera), joinedload(RecognitionEvent.employee))
         .where(RecognitionEvent.event_time >= start, RecognitionEvent.event_time < start + timedelta(days=1))
         .order_by(RecognitionEvent.event_time.desc()).limit(min(limit, 1000)))
    if user.role != Role.admin:
        q = q.where(RecognitionEvent.employee_id.in_(select(Employee.id).where(access.scope_clause(db, user))))
    if decision:
        q = q.where(RecognitionEvent.decision == decision)
    return db.scalars(q).all()
