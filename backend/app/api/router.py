from fastapi import APIRouter

from app.api import attendance, auth, cameras, departments, employees, faces, leave, recognition, reports, schedules

api_router = APIRouter(prefix="/api/v1")
for m in (auth, departments, employees, faces, cameras, schedules, leave, attendance, recognition, reports):
    api_router.include_router(m.router)
