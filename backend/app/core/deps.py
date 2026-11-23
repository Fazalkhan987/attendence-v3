import time

import jwt
from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import decode_token, decrypt_bytes, verify_signature
from app.database import get_db
from app.models import Camera, Role, User

bearer = HTTPBearer(auto_error=False)


def get_current_user(creds: HTTPAuthorizationCredentials = Depends(bearer),
                     db: Session = Depends(get_db)) -> User:
    if not creds:
        raise HTTPException(401, "Not authenticated")
    try:
        payload = decode_token(creds.credentials)
        user = db.get(User, int(payload["sub"]))
    except (jwt.PyJWTError, KeyError, ValueError):
        raise HTTPException(401, "Invalid or expired token")
    if not user or not user.is_active:
        raise HTTPException(401, "Account disabled or not found")
    return user


def require_roles(*roles: Role):
    def dep(user: User = Depends(get_current_user)) -> User:
        if user.role not in roles:
            raise HTTPException(403, "You do not have permission to perform this action")
        return user
    return dep


admin_only = require_roles(Role.admin)
staff_only = require_roles(Role.admin, Role.supervisor)


async def authenticate_camera(request: Request, db: Session = Depends(get_db)) -> Camera:
    """HMAC authentication for the face engine: X-Camera-Id, X-Timestamp, X-Signature."""
    code = request.headers.get("X-Camera-Id")
    ts = request.headers.get("X-Timestamp")
    sig = request.headers.get("X-Signature")
    if not (code and ts and sig):
        raise HTTPException(401, "Missing camera authentication headers")
    camera = db.scalar(select(Camera).where(Camera.camera_code == code))
    if not camera or not camera.is_active:
        raise HTTPException(401, "Unknown or inactive camera")
    try:
        if abs(time.time() - int(ts)) > settings.EVENT_MAX_SKEW_SECONDS:
            raise HTTPException(401, "Stale request timestamp")
    except ValueError:
        raise HTTPException(401, "Bad timestamp")
    body = await request.body()
    secret = decrypt_bytes(camera.secret_enc).decode()
    if not verify_signature(secret, ts, body, sig):
        raise HTTPException(401, "Invalid signature")
    return camera
