import httpx
import numpy as np
from fastapi import HTTPException
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import decrypt_bytes, encrypt_bytes
from app.models import Employee, FaceEmbedding


def enroll(db: Session, emp: Employee, images: list[str]) -> dict:
    try:
        r = httpx.post(f"{settings.FACE_ENGINE_URL}/embed", json={"images": images},
                       headers={"X-Service-Token": settings.FACE_ENGINE_TOKEN}, timeout=120)
        r.raise_for_status()
        results = r.json()["results"]
    except (httpx.HTTPError, KeyError, ValueError):
        raise HTTPException(503, "Face engine is unavailable")

    rejected = [x.get("reason") or "rejected" for x in results if not x.get("ok")]
    good = [x for x in results if x.get("ok")]
    if len(good) < settings.MIN_ENROLL_SAMPLES:
        raise HTTPException(422, f"Need at least {settings.MIN_ENROLL_SAMPLES} good samples; "
                                 f"got {len(good)}. Issues: {', '.join(sorted(set(rejected))) or 'none'}")

    E = np.array([x["embedding"] for x in good], dtype=np.float32)
    E /= np.linalg.norm(E, axis=1, keepdims=True)
    centroid = E.mean(axis=0)
    centroid /= np.linalg.norm(centroid)
    keep = (E @ centroid) >= settings.ENROLL_CONSISTENCY_THRESHOLD
    if keep.sum() < settings.MIN_ENROLL_SAMPLES:
        raise HTTPException(422, "Samples are inconsistent (different people or poor quality). Try again.")
    rejected += ["inconsistent_sample"] * int((~keep).sum())
    E = E[keep]
    qualities = [x.get("quality", 0) for x, k in zip(good, keep) if k]
    centroid = E.mean(axis=0)
    centroid /= np.linalg.norm(centroid)

    # reject if this face already belongs to another employee
    for emp_id, blob in db.execute(select(FaceEmbedding.employee_id, FaceEmbedding.embedding_enc)
                                   .where(FaceEmbedding.employee_id != emp.id)).all():
        other = np.frombuffer(decrypt_bytes(blob), dtype=np.float32)
        if float(other @ centroid) >= settings.DUPLICATE_FACE_THRESHOLD:
            code = db.scalar(select(Employee.employee_code).where(Employee.id == emp_id))
            raise HTTPException(409, f"This face is already enrolled for employee {code}")

    db.execute(delete(FaceEmbedding).where(FaceEmbedding.employee_id == emp.id))
    for vec, q in zip(E, qualities):
        db.add(FaceEmbedding(employee_id=emp.id, quality=float(q),
                             embedding_enc=encrypt_bytes(vec.astype(np.float32).tobytes())))
    return {"stored": int(len(E)), "rejected": rejected}
