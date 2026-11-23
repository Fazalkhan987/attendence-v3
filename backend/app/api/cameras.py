from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.deps import admin_only
from app.core.security import encrypt_bytes, generate_camera_secret
from app.database import get_db
from app.models import Camera, Department, User
from app.schemas import CameraIn, CameraOut, CameraSecretOut, CameraUpdate
from app.services import audit

router = APIRouter(prefix="/cameras", tags=["cameras"])


def _with_secret(cam: Camera, secret: str) -> CameraSecretOut:
    return CameraSecretOut(**CameraOut.model_validate(cam).model_dump(), secret=secret)


@router.get("", response_model=list[CameraOut])
def list_cameras(db: Session = Depends(get_db), _: User = Depends(admin_only)):
    return db.scalars(select(Camera).order_by(Camera.camera_code)).all()


@router.post("", response_model=CameraSecretOut, status_code=201)
def create_camera(data: CameraIn, request: Request, db: Session = Depends(get_db), admin: User = Depends(admin_only)):
    if db.scalar(select(Camera.id).where(Camera.camera_code == data.camera_code)):
        raise HTTPException(409, "Camera ID already exists")
    if data.department_id and not db.get(Department, data.department_id):
        raise HTTPException(400, "Department not found")
    secret = generate_camera_secret()
    cam = Camera(**data.model_dump(), secret_enc=encrypt_bytes(secret.encode()))
    db.add(cam)
    db.flush()
    audit.log(db, admin, "create", "camera", cam.id, {"camera_code": cam.camera_code}, request)
    db.commit()
    return _with_secret(cam, secret)   # shown once


@router.put("/{cam_id}", response_model=CameraOut)
def update_camera(cam_id: int, data: CameraUpdate, request: Request, db: Session = Depends(get_db),
                  admin: User = Depends(admin_only)):
    cam = db.get(Camera, cam_id)
    if not cam:
        raise HTTPException(404, "Camera not found")
    changes = data.model_dump(exclude_unset=True)
    for k, v in changes.items():
        setattr(cam, k, v)
    audit.log(db, admin, "update", "camera", cam.id, changes, request)
    db.commit()
    return cam


@router.post("/{cam_id}/rotate-secret", response_model=CameraSecretOut)
def rotate_secret(cam_id: int, request: Request, db: Session = Depends(get_db), admin: User = Depends(admin_only)):
    cam = db.get(Camera, cam_id)
    if not cam:
        raise HTTPException(404, "Camera not found")
    secret = generate_camera_secret()
    cam.secret_enc = encrypt_bytes(secret.encode())
    audit.log(db, admin, "rotate_secret", "camera", cam.id, request=request)
    db.commit()
    return _with_secret(cam, secret)
