from datetime import datetime
from typing import Any

import httpx
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.core.config import settings

router = APIRouter(prefix="/oracle", tags=["oracle"])


class OracleCast(BaseModel):
    base: str | None = None
    changed: str | None = None
    mutual: str | None = None
    opposite: str | None = None
    reversed: str | None = None
    moving_lines: list[int] = Field(default_factory=list)
    summary: str | None = None


class OracleMessage(BaseModel):
    role: str
    content: str


class OracleChatIn(BaseModel):
    question: str = Field(min_length=1, max_length=800)
    cast: OracleCast | None = None
    current_time: str | None = None
    history: list[OracleMessage] = Field(default_factory=list, max_length=8)


class OracleChatOut(BaseModel):
    answer: str
    model: str


SYSTEM_PROMPT = """你是“玄览”应用里的 AI 国学问卜助手。
定位：传统文化解读、AI 互动娱乐、个人生活建议。
要求：
1. 结合易经卦象、阴阳五行、节气时令、民俗语言给出启发式解读。
2. 不要声称能绝对预测未来，不要用恐吓、宿命论、包治百病或保证发财的表达。
3. 遇到医学、法律、财务、心理危机等高风险问题，要建议咨询专业人士。
4. 不做身份识别、敏感属性判断或人脸生物特征推断。
5. 输出中文，结构为：卦象/时机、现实判断、行动建议、提醒边界。
6. 语气有传统文化韵味，但要清楚、实际、克制。"""


def _cast_context(cast: OracleCast | None) -> str:
    if not cast:
        return "暂无卦象，按当前时间与问题语义做文化化解读。"
    parts = [
        f"本卦：{cast.base or '未提供'}",
        f"变卦：{cast.changed or '未提供'}",
        f"互卦：{cast.mutual or '未提供'}",
        f"错卦：{cast.opposite or '未提供'}",
        f"综卦：{cast.reversed or '未提供'}",
        f"动爻：{','.join(str(x) for x in cast.moving_lines) if cast.moving_lines else '无明显动爻'}",
    ]
    if cast.summary:
        parts.append(f"页面卦义摘要：{cast.summary}")
    return "；".join(parts)


def _normalize_history(history: list[OracleMessage]) -> list[dict[str, str]]:
    normalized: list[dict[str, str]] = []
    for item in history[-6:]:
        if item.role not in {"user", "assistant"}:
            continue
        content = item.content.strip()
        if content:
            normalized.append({"role": item.role, "content": content[:1000]})
    return normalized


@router.post("/chat", response_model=OracleChatOut)
async def chat(data: OracleChatIn) -> OracleChatOut:
    if not settings.deepseek_api_key:
        raise HTTPException(
            status_code=503,
            detail="DeepSeek API Key 未配置。请在 .env 中设置 DEEPSEEK_API_KEY 后重启服务。",
        )

    now_text = data.current_time or datetime.now().isoformat(timespec="seconds")
    user_prompt = f"""当前时间：{now_text}
起卦信息：{_cast_context(data.cast)}
用户问题：{data.question.strip()}

请给出一段完整解读，避免绝对化预测，并给出 3 条可执行建议。"""

    messages: list[dict[str, str]] = [{"role": "system", "content": SYSTEM_PROMPT}]
    messages.extend(_normalize_history(data.history))
    messages.append({"role": "user", "content": user_prompt})

    payload: dict[str, Any] = {
        "model": settings.deepseek_model,
        "messages": messages,
        "temperature": 0.78,
        "max_tokens": 900,
        "thinking": {"type": "disabled"},
        "stream": False,
    }

    url = f"{settings.deepseek_base_url.rstrip('/')}/chat/completions"
    headers = {
        "Authorization": f"Bearer {settings.deepseek_api_key}",
        "Content-Type": "application/json",
    }

    try:
        async with httpx.AsyncClient(timeout=45) as client:
            response = await client.post(url, headers=headers, json=payload)
            response.raise_for_status()
    except httpx.HTTPStatusError as exc:
        detail = exc.response.text[:500] if exc.response is not None else str(exc)
        raise HTTPException(status_code=502, detail=f"DeepSeek 调用失败：{detail}") from exc
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail=f"DeepSeek 网络请求失败：{exc}") from exc

    result = response.json()
    answer = (
        result.get("choices", [{}])[0]
        .get("message", {})
        .get("content", "")
        .strip()
    )
    if not answer:
        raise HTTPException(status_code=502, detail="DeepSeek 返回为空。")

    return OracleChatOut(answer=answer, model=result.get("model") or settings.deepseek_model)
