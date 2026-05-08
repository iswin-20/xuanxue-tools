from sqlalchemy.orm import Session

from app.models.models import ExternalSyncSource


def create_source(db: Session, user_id: int, source_name: str, base_url: str, api_key_hint: str | None = None):
    source = ExternalSyncSource(
        user_id=user_id,
        source_name=source_name,
        base_url=base_url,
        api_key_hint=api_key_hint,
    )
    db.add(source)
    db.commit()
    db.refresh(source)
    return source


def list_sources(db: Session, user_id: int):
    return db.query(ExternalSyncSource).filter(ExternalSyncSource.user_id == user_id).all()
