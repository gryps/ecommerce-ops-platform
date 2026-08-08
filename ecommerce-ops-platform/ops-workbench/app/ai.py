from __future__ import annotations

import json
import re
import time
import urllib.error
import urllib.request
from typing import Any

from app.core.database import session_scope
from app.core.security import utc_now
from app.domain.models import WorkbenchSetting
from app.models import ModelProfile
from app.services.model_call_logs import record_business_model_call


PROFILE_STORAGE_KEY = "model_profiles"
DEFAULT_COMPATIBLE_BASE_URL = ""
PROFILE_STAGES = (
    ("copywriting", "文案生成"),
    ("image_analysis", "原图分析与提示词"),
    ("image_generation", "AI 商品生图"),
    ("speech_recognition", "音频转文案"),
    ("speech_synthesis", "字幕配音"),
)
QWEN3_ASR_HTTP_MODEL_PATTERN = re.compile(
    r"qwen3-asr-flash(?:-\d{4}-\d{2}-\d{2})?",
    re.IGNORECASE,
)


def is_supported_speech_recognition_model(model: str) -> bool:
    """Return whether a model supports the synchronous OpenAI-compatible ASR API."""
    return bool(QWEN3_ASR_HTTP_MODEL_PATTERN.fullmatch(model.strip()))


def models_for_profile_stage(stage: str, models: list[str]) -> list[str]:
    if stage == "speech_recognition":
        return [item for item in models if is_supported_speech_recognition_model(item)]
    return models


def default_profiles() -> list[ModelProfile]:
    return [
        ModelProfile(
            stage=stage,
            label=label,
            base_url=DEFAULT_COMPATIBLE_BASE_URL,
        )
        for stage, label in PROFILE_STAGES
    ]


def mask_api_key(value: str) -> str:
    clean = value.strip()
    return f"****{clean[-4:]}" if clean else ""


def _stored_profiles() -> dict[str, dict[str, Any]]:
    with session_scope() as session:
        setting = session.get(WorkbenchSetting, PROFILE_STORAGE_KEY)
        rows = (setting.value or {}).get("profiles", []) if setting else []
        return {
            str(item.get("stage") or ""): dict(item)
            for item in rows
            if isinstance(item, dict) and item.get("stage")
        }


def load_model_profiles(include_api_key: bool = False) -> list[ModelProfile]:
    stored = _stored_profiles()
    profiles: list[ModelProfile] = []
    for default in default_profiles():
        current = stored.get(default.stage, {})
        api_key = str(current.get("api_key") or "")
        profiles.append(
            ModelProfile(
                stage=default.stage,
                label=default.label,
                base_url=str(current.get("base_url") or default.base_url),
                model=str(current.get("model") or ""),
                temperature=float(current.get("temperature", default.temperature)),
                proxy_url=str(current.get("proxy_url") or ""),
                api_key=api_key if include_api_key else "",
                has_api_key=bool(api_key),
                api_key_mask=mask_api_key(api_key),
            )
        )
    return profiles


def save_model_profiles(profiles: list[ModelProfile]) -> None:
    allowed = {stage for stage, _label in PROFILE_STAGES}
    provided = {item.stage: item for item in profiles if item.stage in allowed}
    if set(provided) != allowed:
        raise ValueError("模型配置不完整，请补齐所有业务模型配置")
    previous = _stored_profiles()
    payload: list[dict[str, Any]] = []
    for stage, _label in PROFILE_STAGES:
        profile = provided[stage]
        old = previous.get(stage, {})
        payload.append(
            {
                "stage": stage,
                "base_url": profile.base_url.strip(),
                "model": profile.model.strip(),
                "temperature": profile.temperature,
                "proxy_url": profile.proxy_url.strip(),
                "api_key": profile.api_key.strip() or str(old.get("api_key") or ""),
            }
        )
    with session_scope() as session:
        setting = session.get(WorkbenchSetting, PROFILE_STORAGE_KEY)
        if setting is None:
            setting = WorkbenchSetting(key=PROFILE_STORAGE_KEY, value={})
            session.add(setting)
        setting.value = {"profiles": payload}
        setting.updated_at = utc_now()


def openai_chat_endpoint(base_url: str) -> str:
    clean = base_url.rstrip("/")
    return f"{clean}/chat/completions" if clean.endswith("/v1") else f"{clean}/v1/chat/completions"


def openai_models_endpoint(base_url: str) -> str:
    clean = base_url.rstrip("/")
    return f"{clean}/models" if clean.endswith("/v1") else f"{clean}/v1/models"


def openai_authorization(api_key: str) -> str:
    clean = api_key.strip()
    if clean.casefold().startswith("bearer "):
        clean = clean[7:].strip()
    return f"Bearer {clean}"


def _profile_urlopen(profile: ModelProfile, request: urllib.request.Request, *, timeout: int):
    proxy_url = profile.proxy_url.strip()
    if not proxy_url:
        return urllib.request.urlopen(request, timeout=timeout)
    if not proxy_url.startswith(("http://", "https://")):
        raise ValueError("模型代理地址必须以 http:// 或 https:// 开头")
    opener = urllib.request.build_opener(
        urllib.request.ProxyHandler({"http": proxy_url, "https": proxy_url})
    )
    return opener.open(request, timeout=timeout)


def list_openai_compatible_models(profile: ModelProfile) -> list[str]:
    if not profile.base_url.strip():
        raise RuntimeError("接口地址不能为空")
    if not profile.api_key.strip():
        raise RuntimeError("API Key 不能为空")
    request = urllib.request.Request(
        openai_models_endpoint(profile.base_url),
        headers={"Authorization": openai_authorization(profile.api_key)},
        method="GET",
    )
    try:
        with _profile_urlopen(profile, request, timeout=30) as response:
            data = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"读取模型列表失败：HTTP {exc.code}: {detail[:500]}") from exc
    except (urllib.error.URLError, TimeoutError, ValueError, TypeError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"读取模型列表失败：{exc}") from exc
    rows = data.get("data") if isinstance(data, dict) else data
    if not isinstance(rows, list):
        raise RuntimeError("模型接口未返回有效的 data 列表")
    models = sorted(
        {
            str(item.get("id") if isinstance(item, dict) else item).strip()
            for item in rows
            if (item.get("id") if isinstance(item, dict) else item)
        },
        key=str.casefold,
    )
    if not models:
        raise RuntimeError("模型接口返回的列表为空")
    return models


def parse_model_json_content(content: Any) -> Any:
    if not isinstance(content, str):
        return content
    clean = content.strip()
    fenced = re.fullmatch(r"```(?:json)?\s*(.*?)\s*```", clean, re.DOTALL | re.IGNORECASE)
    if fenced:
        clean = fenced.group(1).strip()
    try:
        return json.loads(clean)
    except json.JSONDecodeError:
        match = re.search(r"(\{.*\}|\[.*\])", clean, re.DOTALL)
        if match:
            return json.loads(match.group(1))
        raise


def request_openai_chat(
    profile: ModelProfile,
    messages: list[dict],
    stage: str = "copywriting",
    force_json: bool = False,
    *,
    business_step: str = "",
    call_id: str = "",
    attempt_number: int | None = None,
    timeout_seconds: int = 90,
) -> Any:
    payload: dict[str, Any] = {
        "model": profile.model,
        "messages": messages,
        "temperature": profile.temperature,
    }
    if force_json:
        payload["response_format"] = {"type": "json_object"}
    request = urllib.request.Request(
        openai_chat_endpoint(profile.base_url),
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": openai_authorization(profile.api_key),
        },
        method="POST",
    )
    started = time.monotonic()
    data: dict[str, Any] = {}
    try:
        with _profile_urlopen(profile, request, timeout=max(1, timeout_seconds)) as response:
            data = json.loads(response.read().decode("utf-8"))
        content = data["choices"][0]["message"]["content"]
        record_business_model_call(
            stage=stage,
            label=profile.label,
            provider="openai_compatible",
            model=profile.model,
            input_payload=payload,
            output_payload=data,
            success=True,
            duration_ms=int((time.monotonic() - started) * 1000),
            usage=data.get("usage") or {},
            business_step=business_step,
            call_id=call_id,
            attempt_number=attempt_number,
        )
        return parse_model_json_content(content)
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        message = f"HTTP {exc.code}: {detail[:500]}"
        output: Any = {"raw_response": detail}
    except (urllib.error.URLError, TimeoutError) as exc:
        message = f"模型调用失败：{exc}"
        output = {}
    except (ValueError, KeyError, IndexError, TypeError, json.JSONDecodeError) as exc:
        message = f"模型返回结果无效：{exc}"
        output = data
    record_business_model_call(
        stage=stage,
        label=profile.label,
        provider="openai_compatible",
        model=profile.model,
        input_payload=payload,
        output_payload=output,
        success=False,
        duration_ms=int((time.monotonic() - started) * 1000),
        business_step=business_step,
        call_id=call_id,
        attempt_number=attempt_number,
    )
    raise RuntimeError(message)


def test_openai_compatible_profile(profile: ModelProfile) -> dict[str, Any]:
    started = time.monotonic()
    if not profile.base_url.strip():
        return {"success": False, "message": "接口地址不能为空"}
    if not profile.model.strip():
        return {"success": False, "message": "模型不能为空"}
    if not profile.api_key.strip():
        return {"success": False, "message": "API Key 不能为空"}
    request = urllib.request.Request(
        openai_chat_endpoint(profile.base_url),
        data=json.dumps(
            {
                "model": profile.model,
                "messages": [{"role": "user", "content": "请回复：连接测试成功"}],
                "temperature": profile.temperature,
            }
        ).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": openai_authorization(profile.api_key),
        },
        method="POST",
    )
    try:
        with _profile_urlopen(profile, request, timeout=30) as response:
            data = json.loads(response.read().decode("utf-8"))
        message = data["choices"][0]["message"]["content"]
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        return {"success": False, "message": f"HTTP {exc.code}: {detail[:500]}"}
    except (urllib.error.URLError, TimeoutError, ValueError, KeyError, IndexError, TypeError) as exc:
        return {"success": False, "message": str(exc)}
    return {
        "success": True,
        "message": "连接测试成功",
        "latency_ms": int((time.monotonic() - started) * 1000),
        "model": profile.model,
        "provider": "openai_compatible",
        "response_preview": str(message)[:500],
    }
