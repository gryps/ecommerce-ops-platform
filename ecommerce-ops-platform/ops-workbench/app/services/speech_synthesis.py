from __future__ import annotations

import json
from pathlib import Path
import re
import time
import urllib.error
import urllib.request
import wave
from urllib.parse import urlsplit, urlunsplit

from app.ai import (
    _profile_urlopen,
    load_model_profiles,
    openai_authorization,
)
from app.services.model_call_logs import record_business_model_call


def _speech_endpoint(base_url: str) -> str:
    clean = base_url.rstrip("/")
    return f"{clean}/audio/speech" if clean.endswith("/v1") else f"{clean}/v1/audio/speech"


def _workspace_speech_endpoint(base_url: str) -> str:
    """Convert a workspace compatible-mode URL to the native non-streaming TTS URL."""
    parsed = urlsplit(base_url.strip())
    path = parsed.path.rstrip("/")
    for marker in ("/compatible-mode/v1", "/api/v1"):
        if marker in path:
            path = path.split(marker, 1)[0]
            break
    endpoint_path = f"{path}/api/v1/services/audio/tts/SpeechSynthesizer"
    return urlunsplit((parsed.scheme, parsed.netloc, endpoint_path, "", ""))


def _response_audio_url(payload: dict) -> str:
    output = payload.get("output") if isinstance(payload.get("output"), dict) else {}
    audio = output.get("audio") if isinstance(output.get("audio"), dict) else {}
    for value in (audio.get("url"), output.get("url"), payload.get("url")):
        if isinstance(value, str) and value.startswith(("http://", "https://")):
            return value
    raise RuntimeError("配音模型响应中没有音频下载地址")


def generated_subtitle_cues(text: str, audio_path: Path) -> list[dict]:
    """Create deterministic subtitle timing for text whose synthesized audio is known."""
    try:
        with wave.open(str(audio_path), "rb") as source:
            duration = source.getnframes() / max(1, source.getframerate())
    except (OSError, wave.Error, EOFError):
        duration = max(1.0, len(text.strip()) / 4.0)
    parts = [part.strip() for part in re.split(r"(?<=[。！？!?；;\n])", text.strip()) if part.strip()]
    if not parts:
        return []
    weights = [max(1, len(re.sub(r"\s+", "", part))) for part in parts]
    total = sum(weights)
    cues: list[dict] = []
    cursor = 0.0
    for index, (part, weight) in enumerate(zip(parts, weights, strict=True)):
        end = duration if index == len(parts) - 1 else cursor + duration * weight / total
        cues.append({"text": part, "start_seconds": round(cursor, 3), "end_seconds": round(max(end, cursor + 0.001), 3)})
        cursor = end
    return cues


def generate_narration_audio(
    text: str,
    target_path: Path,
    *,
    call_id: str = "",
    voice: str | None = None,
    speed: float | None = None,
    extra_options: dict | None = None,
    business_step: str = "旁白文案模型配音",
) -> dict:
    narration = text.strip()
    if not narration:
        raise ValueError("旁白文案为空，无法生成配音")
    profile = next(
        (
            item
            for item in load_model_profiles(include_api_key=True)
            if item.stage == "speech_synthesis"
        ),
        None,
    )
    if (
        profile is None
        or not profile.base_url
        or not profile.model
        or not profile.api_key
        or not voice
    ):
        raise ValueError("请先在模型配置中完整配置“字幕配音”模型，并输入有效音色序号")
    chosen_voice = voice.strip()
    uses_workspace_tts = profile.model.casefold().startswith("qwen-audio-") or "cosyvoice" in profile.model.casefold()
    if uses_workspace_tts:
        speech_input = {"text": narration, "voice": chosen_voice, "format": "wav", "sample_rate": 24000}
        if speed is not None:
            speech_input["speed"] = max(0.25, min(4.0, float(speed)))
        speech_input.update(dict(extra_options or {}))
        payload = {"model": profile.model, "input": speech_input}
        endpoint = _workspace_speech_endpoint(profile.base_url)
    else:
        payload = {"model": profile.model, "input": narration, "voice": chosen_voice, "response_format": "wav"}
        if speed is not None:
            payload["speed"] = max(0.25, min(4.0, float(speed)))
        payload.update(dict(extra_options or {}))
        endpoint = _speech_endpoint(profile.base_url)
    request = urllib.request.Request(
        endpoint,
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": openai_authorization(profile.api_key),
        },
        method="POST",
    )
    started = time.monotonic()
    try:
        with _profile_urlopen(profile, request, timeout=120) as response:
            response_body = response.read()
        provider_request_id = ""
        if uses_workspace_tts:
            provider_payload = json.loads(response_body.decode("utf-8"))
            provider_request_id = str(provider_payload.get("request_id") or "")
            audio_request = urllib.request.Request(_response_audio_url(provider_payload), method="GET")
            with _profile_urlopen(profile, audio_request, timeout=120) as response:
                audio = response.read()
        else:
            audio = response_body
        if not audio:
            raise RuntimeError("配音模型返回了空音频")
        target_path.parent.mkdir(parents=True, exist_ok=True)
        target_path.write_bytes(audio)
        duration_ms = int((time.monotonic() - started) * 1000)
        record_business_model_call(
            stage=profile.stage,
            label=profile.label,
            provider="bailian",
            model=profile.model,
            input_payload=payload,
            output_payload={"audio_bytes": len(audio), "format": "wav", "provider_request_id": provider_request_id},
            success=True,
            duration_ms=duration_ms,
            business_step=business_step,
            call_id=call_id,
        )
        return {
            "model": profile.model,
            "voice": chosen_voice,
            "audio_bytes": len(audio),
        }
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        message = f"配音模型 HTTP {exc.code}: {detail[:500]}"
    except (urllib.error.URLError, TimeoutError) as exc:
        message = f"配音模型调用失败：{exc}"
    except Exception as exc:
        message = str(exc)
    record_business_model_call(
        stage=profile.stage,
        label=profile.label,
        provider="bailian",
        model=profile.model,
        input_payload=payload,
        output_payload={"error": message},
        success=False,
        duration_ms=int((time.monotonic() - started) * 1000),
        business_step=business_step,
        call_id=call_id,
    )
    raise RuntimeError(message)
