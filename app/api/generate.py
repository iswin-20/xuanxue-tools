from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.schemas import BatchGenerateIn, GenerateIn, GenerationOut
from app.services.auth import get_current_user
from app.services.generation import batch_generate, create_generation_task

router = APIRouter(prefix="/generate", tags=["generate"])


@router.post("", response_model=GenerationOut)
async def generate(data: GenerateIn, db: Session = Depends(get_db), user=Depends(get_current_user)):
    task = await create_generation_task(
        db=db,
        user_id=user.id,
        provider=data.provider,
        model=data.model,
        prompt=data.prompt,
        product_name=data.product_name,
    )
    return task


@router.post("/batch")
async def generate_batch(data: BatchGenerateIn, db: Session = Depends(get_db), user=Depends(get_current_user)):
    batch_id, tasks = await batch_generate(
        db=db,
        user_id=user.id,
        provider=data.provider,
        model=data.model,
        prompt=data.prompt,
        products=data.products,
    )
    return {"batch_id": batch_id, "count": len(tasks), "tasks": tasks}
