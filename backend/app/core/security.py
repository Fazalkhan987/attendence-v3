import hashlib
import hmac
import secrets
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt
from cryptography.fernet import Fernet

from app.core.config import settings

_fernet = Fernet(settings.FERNET_KEY.encode())


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode()[:72], bcrypt.gensalt()).decode()


def verify_password(password: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode()[:72], hashed.encode())
    except ValueError:
        return False


def create_access_token(user_id: int, role: str) -> str:
    exp = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_MINUTES)
    return jwt.encode({"sub": str(user_id), "role": role, "exp": exp},
                      settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


def decode_token(token: str) -> dict:
    return jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])


def encrypt_bytes(data: bytes) -> bytes:
    return _fernet.encrypt(data)


def decrypt_bytes(data: bytes) -> bytes:
    return _fernet.decrypt(data)


def generate_camera_secret() -> str:
    return secrets.token_urlsafe(32)


def sign_request(secret: str, timestamp: str, body: bytes) -> str:
    return hmac.new(secret.encode(), timestamp.encode() + b"." + body, hashlib.sha256).hexdigest()


def verify_signature(secret: str, timestamp: str, body: bytes, signature: str) -> bool:
    return hmac.compare_digest(sign_request(secret, timestamp, body), signature)
