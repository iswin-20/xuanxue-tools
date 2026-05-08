import os
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, UploadFile, HTTPException

from app.core.config import settings
from app.services.auth import get_current_user

router = APIRouter(prefix="/upload", tags=["upload"])


@router.post("/image")
async def upload_image(file: UploadFile = File(...), user=Depends(get_current_user)):
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="Only image files are allowed")

    ext = os.path.splitext(file.filename or "")[1] or ".png"
    name = f"{uuid.uuid4().hex}{ext}"
    out_dir = Path(settings.upload_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / name

    data = await file.read()
    out_path.write_bytes(data)

    return {"url": f"/{settings.upload_dir}/{name}"}
