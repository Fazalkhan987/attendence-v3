import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select

from app import models
from app.api.router import api_router
from app.core.config import settings
from app.core.security import hash_password
from app.database import Base, SessionLocal, engine
from app.services.attendance_service import run_finalize_job

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("main")


def seed() -> None:
    with SessionLocal() as db:
        if not db.scalar(select(models.User.id).where(models.User.role == models.Role.admin).limit(1)):
            db.add(models.User(email=settings.ADMIN_EMAIL.lower(), role=models.Role.admin,
                               password_hash=hash_password(settings.ADMIN_PASSWORD)))
        if not db.scalar(select(models.LeaveType.id).limit(1)):
            db.add_all([models.LeaveType(name=n) for n in ("Casual Leave", "Sick Leave", "Annual Leave", "Other")])
        db.commit()


async def _finalize_loop():
    while True:
        try:
            await asyncio.to_thread(run_finalize_job)
        except Exception:
            log.exception("finalize job failed")
        await asyncio.sleep(settings.FINALIZE_INTERVAL_SECONDS)


@asynccontextmanager
async def lifespan(_: FastAPI):
    Base.metadata.create_all(engine)
    seed()
    task = asyncio.create_task(_finalize_loop())
    yield
    task.cancel()


app = FastAPI(title="Smart Employee Attendance System", version="1.0.0", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=settings.cors_list, allow_credentials=True,
                   allow_methods=["*"], allow_headers=["*"])
app.include_router(api_router)


@app.get("/health")
def health():
    return {"status": "ok"}
