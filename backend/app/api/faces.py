import numpy as np
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.core.deps import admin_only, authenticate_camera
from app.core.security import decrypt_bytes
from app.database import get_db
from app.models import Camera, Employee, EmploymentStatus, FaceEmbedding, User
from app.schemas import EnrollIn, EnrollOut
from app.services import audit, face_service

router = APIRouter(tags=["faces"])


@router.post("/employees/{employee_id}/face/enroll", response_model=EnrollOut)
def enroll_face(employee_id: int, data: EnrollIn, request: Request, db: Session = Depends(get_db),
                admin: User = Depends(admin_only)):
    emp = db.get(Employee, employee_id)
    if not emp:
        raise HTTPException(404, "Employee not found")
    if not emp.face_consent:
        raise HTTPException(400, "Employee has not given biometric consent")
    if emp.status != EmploymentStatus.active:
        raise HTTPException(400, "Employee is not active")
    result = face_service.enroll(db, emp, data.images)
    audit.log(db, admin, "face_enroll", "employee", emp.id, {"samples": result["stored"]}, request)
    db.commit()
    return EnrollOut(employee_id=emp.id, samples_stored=result["stored"], rejected=result["rejected"])


@router.delete("/employees/{employee_id}/face", status_code=204)
def delete_face(employee_id: int, request: Request, db: Session = Depends(get_db),
                admin: User = Depends(admin_only)):
    db.execute(delete(FaceEmbedding).where(FaceEmbedding.employee_id == employee_id))
    audit.log(db, admin, "face_delete", "employee", employee_id, request=request)
    db.commit()


@router.get("/faces/gallery")
def gallery(camera: Camera = Depends(authenticate_camera), db: Session = Depends(get_db)):
    """Embeddings for the face engine (camera-authenticated). Limited to the camera's department."""
    q = select(Employee.id, Employee.employee_code).where(
        Employee.status == EmploymentStatus.active, Employee.face_consent.is_(True))
    if camera.department_id:
        q = q.where(Employee.department_id == camera.department_id)
    codes = dict(db.execute(q).all())
    out: dict[str, list] = {}
    for eid, blob in db.execute(select(FaceEmbedding.employee_id, FaceEmbedding.embedding_enc)
                                .where(FaceEmbedding.employee_id.in_(codes.keys()))).all():
        vec = np.frombuffer(decrypt_bytes(blob), dtype=np.float32).tolist()
        out.setdefault(codes[eid], []).append(vec)
    return {"employees": [{"employee_id": k, "embeddings": v} for k, v in out.items()]}
