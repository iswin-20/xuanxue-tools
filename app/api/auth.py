from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import create_access_token, hash_password, verify_password
from app.db.session import get_db
from app.models.models import User
from app.schemas.schemas import LoginIn, RegisterIn, RequestCodeIn, TokenOut
from app.services.verification import create_and_store_code, send_email_code, validate_code

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/request-code")
def request_code(data: RequestCodeIn, db: Session = Depends(get_db)):
    code = create_and_store_code(db, data.email)
    try:
        send_email_code(data.email, code)
    except Exception as exc:
        if settings.app_env.lower() == "dev":
            return {
                "message": f"Email send failed in dev mode: {exc}",
                "debug_code": code,
            }
        raise HTTPException(status_code=400, detail=f"Failed to send verification email: {exc}")
    return {"message": "Verification code sent"}


@router.post("/register")
def register(data: RegisterIn, db: Session = Depends(get_db)):
    if db.query(User).filter(User.email == data.email).first():
        raise HTTPException(status_code=400, detail="Email already registered")
    if not validate_code(db, data.email, data.code):
        raise HTTPException(status_code=400, detail="Invalid or expired code")

    user = User(email=data.email, password_hash=hash_password(data.password), role="user")
    db.add(user)
    db.commit()
    return {"message": "Registration success"}


@router.post("/login", response_model=TokenOut)
def login(data: LoginIn, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == data.email).first()
    if not user or not verify_password(data.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    token = create_access_token(user.email)
    return TokenOut(access_token=token)
