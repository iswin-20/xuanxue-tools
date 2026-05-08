from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.models import PromptLibrary
from app.schemas.schemas import PromptIn, PromptOut
from app.services.auth import get_current_user

router = APIRouter(prefix="/prompts", tags=["prompts"])


@router.post("", response_model=PromptOut)
def create_prompt(data: PromptIn, db: Session = Depends(get_db), user=Depends(get_current_user)):
    item = PromptLibrary(user_id=user.id, **data.model_dump())
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


@router.get("", response_model=list[PromptOut])
def list_prompts(db: Session = Depends(get_db), user=Depends(get_current_user)):
    return (
        db.query(PromptLibrary)
        .filter(PromptLibrary.user_id == user.id)
        .order_by(PromptLibrary.created_at.desc())
        .all()
    )
