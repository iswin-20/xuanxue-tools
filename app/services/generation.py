import uuid
from typing import Iterable

from sqlalchemy.orm import Session

from app.models.models import GenerationTask
from app.providers.providers import ProviderError, generate_with_provider


async def create_generation_task(
    db: Session,
    user_id: int,
    provider: str,
    model: str,
    prompt: str,
    product_name: str | None = None,
    batch_id: str | None = None,
):
    task = GenerationTask(
        user_id=user_id,
        provider=provider,
        model=model,
        prompt=prompt,
        status="queued",
        product_name=product_name,
        batch_id=batch_id,
    )
    db.add(task)
    db.commit()
    db.refresh(task)

    try:
        output_url = await generate_with_provider(provider, prompt, model)
        task.status = "done"
        task.output_url = output_url
    except ProviderError as exc:
        task.status = f"failed: {exc}"
    db.add(task)
    db.commit()
    db.refresh(task)
    return task


async def batch_generate(db: Session, user_id: int, provider: str, model: str, prompt: str, products: Iterable[str]):
    batch_id = uuid.uuid4().hex[:12]
    created = []
    for p in products:
        final_prompt = f"{prompt}\nProduct: {p}" if p else prompt
        item = await create_generation_task(
            db=db,
            user_id=user_id,
            provider=provider,
            model=model,
            prompt=final_prompt,
            product_name=p,
            batch_id=batch_id,
        )
        created.append(item)
    return batch_id, created
