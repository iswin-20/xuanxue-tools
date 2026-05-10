from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from app.api import auth, generate, oracle, prompts, sync, upload
from app.core.config import settings
from app.db.session import Base, engine

Base.metadata.create_all(bind=engine)
Path(settings.upload_dir).mkdir(parents=True, exist_ok=True)

app = FastAPI(title=settings.app_name)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(prompts.router)
app.include_router(generate.router)
app.include_router(upload.router)
app.include_router(sync.router)
app.include_router(oracle.router)

app.mount(f"/{settings.upload_dir}", StaticFiles(directory=settings.upload_dir), name="uploads")
app.mount("/web", StaticFiles(directory="web", html=True), name="web")
app.mount("/assets", StaticFiles(directory="web/assets"), name="assets")


@app.get("/")
def root():
    return FileResponse("web/index.html")
