from __future__ import annotations

from typing import Any

from app.ai import load_model_profiles, request_openai_chat


LANGUAGE_KEYS = ("language_style", "word_preference", "emotional_tone", "appeal_focus")
AUDIENCE_KEYS = ("age", "gender", "interests", "spending_level", "psychological_state")


def _profile():
    profile = next(
        (item for item in load_model_profiles(include_api_key=True) if item.stage == "copywriting"),
        None,
    )
    if not profile or not profile.base_url or not profile.model or not profile.api_key:
        raise ValueError("请先在模型配置中完整配置“文案生成”模型")
    return profile


def _five_copies(parsed: Any) -> list[str]:
    raw = parsed.get("copies") if isinstance(parsed, dict) else None
    if not isinstance(raw, list):
        raise RuntimeError("文案模型返回结果无效：缺少 copies")
    result: list[str] = []
    seen: set[str] = set()
    for value in raw:
        text = str(value).strip()
        normalized = text.casefold()
        if text and normalized not in seen:
            seen.add(normalized)
            result.append(text[:20000])
        if len(result) == 5:
            break
    if len(result) != 5:
        raise RuntimeError("文案模型没有返回 5 条有效且互不重复的文案")
    return result


def analyze_and_generate_copies(*, reference_text: str, source_mode: str) -> dict[str, Any]:
    reference = reference_text.strip()
    if not reference:
        raise ValueError("没有可供分析的参考文案")
    mode_note = (
        "这是用户本次输入的一条参考文案。保持它的内容类型和大致长度：短文案仿写为短文案，长口播稿仿写为相近长度的口播稿。"
        if source_mode == "input"
        else "这是全局已采纳文案形成的历史语料。请归纳共同基调，再生成符合该基调的新文案。"
    )
    parsed = request_openai_chat(
        _profile(),
        [
            {
                "role": "system",
                "content": (
                    "你是短视频文案分析与仿写专家。先分析语言特征和目标受众，再自由推断一个最匹配的专家角色，"
                    "随后生成5条自然、彼此不同的仿写。不得编造参考资料中没有的产品事实。"
                    f"{mode_note}只返回JSON，结构为："
                    '{"language_analysis":{"language_style":"","word_preference":"","emotional_tone":"","appeal_focus":""},'
                    '"audience_analysis":{"age":"","gender":"","interests":"","spending_level":"","psychological_state":""},'
                    '"expert_role":"","copies":["","","","",""]}。所有分析值和专家角色必须使用简洁中文。'
                ),
            },
            {"role": "user", "content": f"参考文案：\n{reference}"},
        ],
        stage="copywriting",
        force_json=True,
        business_step="文案分析与首轮迭代",
    )
    language_raw = parsed.get("language_analysis") if isinstance(parsed, dict) else None
    audience_raw = parsed.get("audience_analysis") if isinstance(parsed, dict) else None
    expert_role = str(parsed.get("expert_role") or "").strip() if isinstance(parsed, dict) else ""
    if not isinstance(language_raw, dict) or not isinstance(audience_raw, dict) or not expert_role:
        raise RuntimeError("文案模型返回结果无效：分析或专家角色不完整")
    language = {key: str(language_raw.get(key) or "").strip() for key in LANGUAGE_KEYS}
    audience = {key: str(audience_raw.get(key) or "").strip() for key in AUDIENCE_KEYS}
    if not all(language.values()) or not all(audience.values()):
        raise RuntimeError("文案模型返回结果无效：分析字段不完整")
    return {
        "language_analysis": language,
        "audience_analysis": audience,
        "expert_role": expert_role[:4000],
        "copies": _five_copies(parsed),
    }


def continue_copy_iteration(
    *,
    reference_text: str,
    language_analysis: dict[str, Any],
    audience_analysis: dict[str, Any],
    expert_role: str,
    reviewed_feedback: list[dict[str, str]],
) -> list[str]:
    feedback = "\n".join(
        f"- {item['status']}：{item['content']}"
        + (f"；原因：{item['reason']}" if item.get("reason") else "")
        for item in reviewed_feedback[-100:]
    ) or "暂无人工审核反馈"
    parsed = request_openai_chat(
        _profile(),
        [
            {
                "role": "system",
                "content": (
                    "你负责继续迭代短视频文案。沿用给定原始资料、语言分析、受众分析和专家角色；"
                    "强化已采纳文案的有效特征，并针对未采纳原因进行改进。保持原文的内容类型和大致长度，"
                    "不编造产品事实。只返回JSON：{\"copies\":[\"\",\"\",\"\",\"\",\"\"]}。"
                ),
            },
            {
                "role": "user",
                "content": (
                    f"原始参考资料：\n{reference_text}\n\n语言分析：{language_analysis}\n"
                    f"受众分析：{audience_analysis}\n专家角色：{expert_role}\n\n审核反馈：\n{feedback}"
                ),
            },
        ],
        stage="copywriting",
        force_json=True,
        business_step="文案继续迭代",
    )
    return _five_copies(parsed)
