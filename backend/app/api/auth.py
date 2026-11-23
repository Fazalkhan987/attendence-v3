from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.core.security import create_access_token, hash_password, verify_password
from app.database import get_db
from app.models import User
from app.schemas import ChangePasswordIn, EmployeeOut, LoginIn, MeOut, TokenOut, UserOut
from app.services import access, audit

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=TokenOut)
def login(data: LoginIn, request: Request, db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(User.email == data.email.strip().lower()))
    if not user or not user.is_active or not verify_password(data.password, user.password_hash):
        audit.log(db, None, "login_failed", "user", data.email[:100], request=request)
        db.commit()
        raise HTTPException(401, "Invalid email or password")
    user.last_login = datetime.now(timezone.utc)
    audit.log(db, user, "login", "user", user.id, request=request)
    db.commit()
    return TokenOut(access_token=create_access_token(user.id, user.role.value), role=user.role)


@router.get("/me", response_model=MeOut)
def me(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    emp = access.my_employee(db, user)
    return MeOut(user=UserOut.model_validate(user),
                 employee=EmployeeOut.model_validate(emp) if emp else None)


@router.post("/change-password", status_code=204)
def change_password(data: ChangePasswordIn, request: Request, user: User = Depends(get_current_user),
                    db: Session = Depends(get_db)):
    if not verify_password(data.current_password, user.password_hash):
        raise HTTPException(400, "Current password is incorrect")
    user.password_hash = hash_password(data.new_password)
    audit.log(db, user, "change_password", "user", user.id, request=request)
    db.commit()
