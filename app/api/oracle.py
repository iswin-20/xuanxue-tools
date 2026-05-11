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
    # 梅花易数体用生克
    ti_gua: str | None = None          # 体卦名
    yong_gua: str | None = None        # 用卦名
    ti_element: str | None = None      # 体卦五行
    yong_element: str | None = None    # 用卦五行
    ti_yong_relation: str | None = None  # 体用关系（用生体/体生用/体用比和/用克体/体克用）


class IChingReadingOut(BaseModel):
    overview: str
    career: str
    relationship: str
    wealth: str
    health: str
    decision: str
    model: str
    # 解卦方法说明
    interpretation_rule: str | None = None
    ti_yong_analysis: str | None = None


SYSTEM_PROMPT = """你是“安安”应用里的 AI 国学与民俗文化解读助手。
定位：传统文化解读、AI 互动娱乐、个人生活建议。
要求：
1. 结合易经、阴阳五行、节气时令、民俗语言给出启发式解读。
2. 不要声称能绝对预测未来，不要用恐吓、宿命论、包治百病或保证发财的表达。
3. 遇到医学、法律、财务、心理危机等高风险问题，要建议咨询专业人士。
4. 不做身份识别、敏感属性判断、人脸识别或生物特征确认。
5. 输出中文，清楚、实际、克制，有传统文化韵味。
6. 说话要通俗易懂，像朋友认真解释一样，少用术语；如果用了卦名、五行词，要马上翻译成大白话。
7. 排版要一条一条整齐输出，多用短句和换行，不要写成一大段。
8. 不要使用 Markdown 格式，不要用 **、###、- 等符号做标题或强调，直接用普通中文编号。
9. 明确说明内容仅供娱乐与传统文化参考。"""


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

【语言要求 - 非常重要】
用非常通俗易懂的大白话解释，就像朋友聊天一样。避免使用文言文、古语、专业术语。
每句话都要让普通人一听就明白。可以举生活中的例子。

【解卦框架】
一、察大象（看大环境）：先看本卦卦名与卦象，判断整体格局好坏。
二、定焦点（看动爻）：根据动爻数量按古法规则解读：
- 0个动爻（六爻安静）：看本卦卦辞
- 1个动爻：看该动爻的爻辞
- 2个动爻：看两个动爻的爻辞，以上方的为主
- 3个动爻：结合本卦和变卦的卦辞综合看
- 4个动爻：看变卦的两个静爻的爻辞，以下方的为主
- 5个动爻：看变卦那一个静爻的爻辞
- 6个动爻：乾坤看用九/用六，他卦看变卦卦辞
三、审体用（梅花易数生克）：如提供了体用信息，参考体用生克关系辅助判断。
四、观始终（看趋势）：从本卦经过互卦走向变卦，给出完整趋势。

【输出要求】
只能使用用户提供的卦名和卦义，不得篡改卦名。
用最通俗的大白话输出，避免古文，多举生活化的例子。
输出必须是一个 JSON 对象，不要 Markdown，不要代码块，字段为：
overview, career, relationship, wealth, health, decision, interpretation_rule, ti_yong_analysis。
每个字段 60 到 120 个中文字符，要说得清楚、明白、接地气。
health 字段只能给作息、压力、运动、饮食节律等生活建议，不要做疾病诊断。
decision 字段要给具体可操作的建议，不要讲空话套话，不要绝对预测。"""


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

    answer = answer.replace("**", "")

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

请按下面格式输出，语言一定要通俗、具体、整齐。
不要使用任何 Markdown 符号，不要出现 **，不要加粗标题，不要用星号列表。
1. 先说结论：用 1 到 2 句话直接回答用户最关心的问题。
2. 卦象怎么看：把本卦、变卦、动爻翻译成普通人能懂的话，不要堆术语。
3. 现在的关键点：列 2 到 3 条，每条一句话。
4. 可以怎么做：给 3 条可执行建议，每条都要具体。
5. 提醒一句：说明仅供传统文化参考，不要绝对化预测。

不要写成长段落，不要文言文，不要吓人，不要保证结果。"""

    messages: list[dict[str, str]] = [{"role": "system", "content": SYSTEM_PROMPT}]
    messages.extend(_normalize_history(data.history))
    messages.append({"role": "user", "content": user_prompt})
    return await _deepseek_chat(messages)


@router.post("/iching-reading", response_model=IChingReadingOut)
async def iching_reading(data: IChingReadingIn) -> IChingReadingOut:
    now_text = data.current_time or datetime.now().isoformat(timespec="seconds")
    moving = "、".join(str(x) for x in data.moving_lines) if data.moving_lines else "无明显动爻"
    moving_count = len(data.moving_lines)
    
    # 确定解卦规则
    if moving_count == 0:
        rule_text = "六爻安静，无动爻（无变卦）。看本卦卦辞作为总体评判。"
    elif moving_count == 1:
        rule_text = f"一爻动（第{data.moving_lines[0]}爻），看本卦该动爻的爻辞。"
    elif moving_count == 2:
        rule_text = f"两爻动（第{'、'.join(str(x) for x in data.moving_lines)}爻），看本卦这两个动爻的爻辞，以上方动爻（第{max(data.moving_lines)}爻）为主。"
    elif moving_count == 3:
        rule_text = "三爻动，结合本卦卦辞和变卦卦辞综合来看。"
    elif moving_count == 4:
        rule_text = "四爻动，看变卦的两个静爻的爻辞，以下方静爻为主。"
    elif moving_count == 5:
        rule_text = "五爻动，看变卦的那一个静爻的爻辞。"
    else:
        rule_text = "六爻全动，乾卦看用九辞，坤卦看用六辞，他卦看变卦卦辞。"
    
    # 体用生克信息
    ti_yong_text = ""
    if data.ti_gua and data.yong_gua:
        ti_yong_text = f"{data.ti_gua}（{data.ti_element}）为体卦（代表求测者），{data.yong_gua}（{data.yong_element}）为用卦（代表事情），体用关系为{data.ti_yong_relation}。"

    user_prompt = f"""当前时间：{now_text}
用户所问：{data.question or '未设问题'}
本卦：{data.base}，卦义：{data.base_text or '未提供'}
变卦：{data.changed}，卦义：{data.changed_text or '未提供'}
互卦：{data.mutual or '未提供'}
错卦：{data.opposite or '未提供'}
综卦：{data.reversed or '未提供'}
动爻：{moving}
解卦规则：{rule_text}
{ti_yong_text}

禁止出现未在上面列出的卦名；禁止把本卦或变卦改写成其他卦。
请按提示词要求输出严格 JSON。"""
    parsed, model = await _deepseek_json(
        [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "system", "content": ICHING_FIELD_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        max_tokens=900,
    )
    required = ["overview", "career", "relationship", "wealth", "health", "decision"]
    missing = [key for key in required if not str(parsed.get(key, "")).strip()]
    if missing:
        raise HTTPException(status_code=502, detail=f"DeepSeek 返回缺少字段：{', '.join(missing)}")
    
    interpretation_rule = str(parsed.get("interpretation_rule", rule_text)).strip()
    ti_yong_analysis = str(parsed.get("ti_yong_analysis", ti_yong_text)).strip()
    
    return IChingReadingOut(
        model=model,
        interpretation_rule=interpretation_rule,
        ti_yong_analysis=ti_yong_analysis,
        **{key: str(parsed[key]).strip() for key in required}
    )


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
