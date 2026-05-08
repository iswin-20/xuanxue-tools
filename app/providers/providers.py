import base64
import uuid
from pathlib import Path

import httpx

from app.core.config import settings


class ProviderError(Exception):
    pass


class BaseProvider:
    name = "base"

    async def generate(self, prompt: str, model: str) -> str:
        raise NotImplementedError

    @staticmethod
    def _save_image_bytes(content: bytes, suffix: str = ".png") -> str:
        out_dir = Path(settings.upload_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        name = f"{uuid.uuid4().hex}{suffix}"
        path = out_dir / name
        path.write_bytes(content)
        return f"/{settings.upload_dir}/{name}"


class GeminiProvider(BaseProvider):
    name = "gemini"

    async def generate(self, prompt: str, model: str) -> str:
        api_key = settings.gemini_api_key
        if not api_key:
            raise ProviderError("Missing GEMINI_API_KEY")

        url = f"{settings.gemini_base_url}/v1beta/models/{model}:generateContent"
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"responseModalities": ["IMAGE", "TEXT"]},
        }

        async with httpx.AsyncClient(timeout=90) as client:
            resp = await client.post(url, params={"key": api_key}, json=payload)
            if resp.status_code >= 400:
                raise ProviderError(f"Gemini API error: {resp.status_code} {resp.text[:300]}")
            data = resp.json()

        candidates = data.get("candidates", [])
        if not candidates:
            raise ProviderError("Gemini API returned empty candidates")

        parts = candidates[0].get("content", {}).get("parts", [])
        for part in parts:
            inline = part.get("inlineData") or part.get("inline_data")
            if inline and inline.get("data"):
                mime_type = inline.get("mimeType") or inline.get("mime_type") or "image/png"
                suffix = ".jpg" if ("jpeg" in mime_type or "jpg" in mime_type) else ".png"
                content = base64.b64decode(inline["data"])
                return self._save_image_bytes(content, suffix=suffix)

        raise ProviderError("Gemini API returned no image data")


class DoubaoProvider(BaseProvider):
    name = "doubao"

    async def generate(self, prompt: str, model: str) -> str:
        api_key = settings.doubao_api_key
        base_url = settings.doubao_base_url
        if not api_key or not base_url:
            raise ProviderError("Missing DOUBAO_API_KEY or DOUBAO_BASE_URL")

        images_url = f"{base_url.rstrip('/')}/images/generations"
        payload = {
            "model": model,
            "prompt": prompt,
            "size": "1024x1024",
            "response_format": "url",
        }

        async with httpx.AsyncClient(timeout=90) as client:
            resp = await client.post(
                images_url,
                headers={"Authorization": f"Bearer {api_key}"},
                json=payload,
            )
            if resp.status_code >= 400:
                raise ProviderError(f"Doubao API error: {resp.status_code} {resp.text[:300]}")
            data = resp.json()
            items = data.get("data", [])
            if not items:
                raise ProviderError("Doubao API returned empty data")
            image_url = items[0].get("url")
            b64_data = items[0].get("b64_json")

            if image_url:
                img = await client.get(image_url)
                if img.status_code >= 400:
                    raise ProviderError(f"Doubao image download error: {img.status_code}")
                return self._save_image_bytes(img.content, suffix=".png")

            if b64_data:
                return self._save_image_bytes(base64.b64decode(b64_data), suffix=".png")

        raise ProviderError("Doubao API returned no image url/base64")


PROVIDERS = {
    GeminiProvider.name: GeminiProvider(),
    DoubaoProvider.name: DoubaoProvider(),
}


async def generate_with_provider(provider: str, prompt: str, model: str) -> str:
    item = PROVIDERS.get(provider.lower())
    if not item:
        raise ProviderError(f"Unsupported provider: {provider}")
    return await item.generate(prompt, model)
