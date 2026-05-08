from datetime import datetime
import asyncio

from sqlalchemy import select

from app.db.session import SessionLocal
from app.models.models import ExternalSyncSource
from app.services.generation import batch_generate


async def run(prompt: str, provider: str, model: str, source_id: int):
    db = SessionLocal()
    try:
        source = db.scalar(select(ExternalSyncSource).where(ExternalSyncSource.id == source_id))
        if not source:
            print(f"[{datetime.now()}] source not found: {source_id}")
            return

        # Placeholder product list; replace by real pulled items from external API.
        products = ["Product-A", "Product-B", "Product-C"]
        batch_id, tasks = await batch_generate(
            db=db,
            user_id=source.user_id,
            provider=provider,
            model=model,
            prompt=prompt,
            products=products,
        )
        print(f"[{datetime.now()}] batch={batch_id} count={len(tasks)}")
    finally:
        db.close()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--prompt", required=True)
    parser.add_argument("--provider", default="gemini")
    parser.add_argument("--model", default="gemini-2.0-flash-preview-image-generation")
    parser.add_argument("--source-id", type=int, required=True)
    args = parser.parse_args()

    asyncio.run(run(args.prompt, args.provider, args.model, args.source_id))
