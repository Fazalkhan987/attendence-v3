from fastapi import Request
from sqlalchemy.orm import Session

from app.models import AuditLog, User


def client_ip(request: Request | None) -> str | None:
    return request.client.host if request and request.client else None


def log(db: Session, user: User | None, action: str, entity: str, entity_id=None,
        details: dict | None = None, request: Request | None = None) -> None:
    db.add(AuditLog(user_id=user.id if user else None, action=action, entity=entity,
                    entity_id=str(entity_id) if entity_id is not None else None,
                    details=details, ip=client_ip(request)))
