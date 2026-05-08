import json
from datetime import datetime
from typing import Any, Literal

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


class CultureReadingIn(BaseModel):
    reading_type: Literal["palm", "face"]
    image_context: str = Field(default="", max_length=1000)
    current_time: str | None = None


class IChingReadingIn(BaseModel):
    question: str = Field(default="未设问题", max_length=800)
    base: str
    changed: str
    mutual: str | None = None
    opposite: str | None = None
    reversed: str | None = None
    moving_lines: list[int] = Field(default_factory=list)
    base_text: str | None = None
    changed_text: str | None = None
    current_time: str | None = None


class IChingReadingOut(BaseModel):
    overview: str
    career: str
    relationship: str
    wealth: str
    health: str
    decision: str
    model: str


SYSTEM_PROMPT = """你是“安安”应用里的 AI 国学与民俗文化解读助手。
定位：传统文化解读、AI 互动娱乐、个人生活建议。
要求：
1. 结合易经、阴阳五行、节气时令、民俗语言给出启发式解读。
2. 不要声称能绝对预测未来，不要用恐吓、宿命论、包治百病或保证发财的表达。
3. 遇到医学、法律、财务、心理危机等高风险问题，要建议咨询专业人士。
4. 不做身份识别、敏感属性判断、人脸识别或生物特征确认。
5. 输出中文，清楚、实际、克制，有传统文化韵味。
6. 明确说明内容仅供娱乐与传统文化参考。"""


PALM_PROMPT = """你正在为“传统手相 AI”模块生成娱乐性文化解读。
请围绕生命线、智慧线、感情线、事业线四个维度输出。
不要声称真实识别了医学健康状况，不要做疾病、寿命、身份或敏感属性判断。
请给出：
1. 总体气质
2. 四条掌纹的传统说法
3. 近期生活建议
4. 边界提醒"""


FACE_PROMPT = """你正在为“传统面相 AI”模块生成娱乐性文化解读。
请围绕脸型气质、额头、眉眼、鼻相、嘴相五个维度输出。
不要做身份识别，不要推断种族、年龄、健康、财富真实性等敏感或高风险结论。
请给出：
1. 总体气质
2. 五官与脸型的传统文化说法
3. 人际沟通与生活建议
4. 隐私与边界提醒"""


ICHING_FIELD_PROMPT = """你正在为“易经算卦”模块生成分领域解读。
必须严格结合本卦、变卦、互卦、错卦、综卦、动爻和用户问题。
只能使用用户提供的卦名和卦义，不要自行推导、替换或新增卦名。
如果用户提供“本卦：屯，变卦：泰”，就必须按屯变泰解释，不得写成其他卦。
不要输出固定模板；不同卦象要体现不同侧重。
输出必须是一个 JSON 对象，不要 Markdown，不要代码块，字段为：
overview, career, relationship, wealth, health, decision。
每个字段 45 到 90 个中文字符。
health 字段只能给作息、压力、运动、饮食节律等生活建议，不要做疾病诊断。
decision 字段要给现实可执行的判断方式，不要绝对预测。"""


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


def _extract_json_object(text: str) -> dict[str, Any]:
    clean = text.strip()
    if clean.startswith("```"):
        clean = clean.strip("`")
        clean = clean.removeprefix("json").strip()
    start = clean.find("{")
    end = clean.rfind("}")
    if start == -1 or end == -1 or end <= start:
        raise ValueError("No JSON object found")
    return json.loads(clean[start : end + 1])


async def _deepseek_chat(messages: list[dict[str, str]], max_tokens: int = 900) -> OracleChatOut:
    if not settings.deepseek_api_key:
        raise HTTPException(
            status_code=503,
            detail="DeepSeek API Key 未配置。请在 .env 中设置 DEEPSEEK_API_KEY 后重启服务。",
        )

    payload: dict[str, Any] = {
        "model": settings.deepseek_model,
        "messages": messages,
        "temperature": 0.78,
        "max_tokens": max_tokens,
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


async def _deepseek_json(messages: list[dict[str, str]], max_tokens: int = 900) -> tuple[dict[str, Any], str]:
    result = await _deepseek_chat(messages, max_tokens=max_tokens)
    try:
        return _extract_json_object(result.answer), result.model
    except (json.JSONDecodeError, ValueError) as exc:
        raise HTTPException(status_code=502, detail=f"DeepSeek JSON 解析失败：{exc}") from exc


@router.post("/chat", response_model=OracleChatOut)
async def chat(data: OracleChatIn) -> OracleChatOut:
    now_text = data.current_time or datetime.now().isoformat(timespec="seconds")
    user_prompt = f"""当前时间：{now_text}
起卦信息：{_cast_context(data.cast)}
用户问题：{data.question.strip()}

请给出一段完整解读，避免绝对化预测，并给出 3 条可执行建议。"""

    messages: list[dict[str, str]] = [{"role": "system", "content": SYSTEM_PROMPT}]
    messages.extend(_normalize_history(data.history))
    messages.append({"role": "user", "content": user_prompt})
    return await _deepseek_chat(messages)


@router.post("/iching-reading", response_model=IChingReadingOut)
async def iching_reading(data: IChingReadingIn) -> IChingReadingOut:
    now_text = data.current_time or datetime.now().isoformat(timespec="seconds")
    moving = "、".join(str(x) for x in data.moving_lines) if data.moving_lines else "无明显动爻"
    user_prompt = f"""当前时间：{now_text}
用户所问：{data.question or '未设问题'}
本卦：{data.base}，卦义：{data.base_text or '未提供'}
变卦：{data.changed}，卦义：{data.changed_text or '未提供'}
互卦：{data.mutual or '未提供'}
错卦：{data.opposite or '未提供'}
综卦：{data.reversed or '未提供'}
动爻：{moving}

禁止出现未在上面列出的卦名；禁止把本卦或变卦改写成其他卦。
请按提示词要求输出严格 JSON。"""
    parsed, model = await _deepseek_json(
        [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "system", "content": ICHING_FIELD_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        max_tokens=700,
    )
    required = ["overview", "career", "relationship", "wealth", "health", "decision"]
    missing = [key for key in required if not str(parsed.get(key, "")).strip()]
    if missing:
        raise HTTPException(status_code=502, detail=f"DeepSeek 返回缺少字段：{', '.join(missing)}")
    return IChingReadingOut(model=model, **{key: str(parsed[key]).strip() for key in required})


@router.post("/culture-reading", response_model=OracleChatOut)
async def culture_reading(data: CultureReadingIn) -> OracleChatOut:
    now_text = data.current_time or datetime.now().isoformat(timespec="seconds")
    module_prompt = PALM_PROMPT if data.reading_type == "palm" else FACE_PROMPT
    user_prompt = f"""当前时间：{now_text}
页面侧摘要：{data.image_context or '用户已上传图片，但未提供可确认的视觉特征。'}

请基于页面侧摘要与传统文化语汇生成解读。注意：不要声称进行了确定性识别；不要输出医学、身份、敏感属性判断。"""
    return await _deepseek_chat(
        [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "system", "content": module_prompt},
            {"role": "user", "content": user_prompt},
        ],
        max_tokens=850,
    )
