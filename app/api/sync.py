from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.schemas import SyncSourceIn
from app.services.auth import get_current_user
from app.sync.sync_service import create_source, list_sources

router = APIRouter(prefix="/sync", tags=["sync"])


@router.post("/sources")
def add_source(data: SyncSourceIn, db: Session = Depends(get_db), user=Depends(get_current_user)):
    return create_source(
        db=db,
        user_id=user.id,
        source_name=data.source_name,
        base_url=data.base_url,
        api_key_hint=data.api_key_hint,
    )


@router.get("/sources")
def get_sources(db: Session = Depends(get_db), user=Depends(get_current_user)):
    return list_sources(db=db, user_id=user.id)


@router.post("/pull-products")
def pull_products(source_id: int, user=Depends(get_current_user)):
    # Placeholder for external site product synchronization.
    # Integrate your other website API here and normalize product payload.
    return {
        "message": "Sync entrypoint created",
        "source_id": source_id,
        "next": "Implement provider-specific pull logic in app/sync",
    }
