from datetime import datetime
from pydantic import BaseModel, EmailStr


class RequestCodeIn(BaseModel):
    email: EmailStr


class RegisterIn(BaseModel):
    email: EmailStr
    password: str
    code: str


class LoginIn(BaseModel):
    email: EmailStr
    password: str


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserOut(BaseModel):
    id: int
    email: EmailStr
    role: str
    is_active: bool

    class Config:
        from_attributes = True


class PromptIn(BaseModel):
    title: str
    prompt_text: str
    preview_image_url: str | None = None
    tags: str | None = None


class PromptOut(PromptIn):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True


class GenerateIn(BaseModel):
    provider: str
    model: str
    prompt: str
    product_name: str | None = None


class BatchGenerateIn(BaseModel):
    provider: str
    model: str
    prompt: str
    products: list[str]


class GenerationOut(BaseModel):
    id: int
    provider: str
    model: str
    prompt: str
    status: str
    output_url: str | None
    product_name: str | None
    batch_id: str | None

    class Config:
        from_attributes = True


class SyncSourceIn(BaseModel):
    source_name: str
    base_url: str
    api_key_hint: str | None = None
