import random
import smtplib
from datetime import datetime, timedelta, timezone
from email.message import EmailMessage

from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import hash_password, verify_password
from app.models.models import VerificationCode


def create_code() -> str:
    return "".join(str(random.randint(0, 9)) for _ in range(6))


def create_and_store_code(db: Session, email: str) -> str:
    code = create_code()
    item = VerificationCode(
        email=email,
        code_hash=hash_password(code),
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=10),
    )
    db.add(item)
    db.commit()
    return code


def validate_code(db: Session, email: str, code: str) -> bool:
    record = (
        db.query(VerificationCode)
        .filter(VerificationCode.email == email, VerificationCode.used == False)
        .order_by(VerificationCode.created_at.desc())
        .first()
    )
    if not record:
        return False
    if record.expires_at < datetime.now(timezone.utc):
        return False
    if not verify_password(code, record.code_hash):
        return False
    record.used = True
    db.add(record)
    db.commit()
    return True


def send_email_code(email: str, code: str):
    if not settings.smtp_username or not settings.smtp_password:
        raise RuntimeError("SMTP not configured. Please set SMTP_USERNAME/SMTP_PASSWORD.")

    msg = EmailMessage()
    msg["Subject"] = f"{settings.app_name} verification code"
    msg["From"] = settings.smtp_from or settings.smtp_username
    msg["To"] = email
    msg.set_content(f"Your verification code is: {code}. It will expire in 10 minutes.")

    with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=10) as server:
        server.starttls()
        server.login(settings.smtp_username, settings.smtp_password)
        server.send_message(msg)
