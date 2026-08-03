from __future__ import annotations

import base64
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Any

import httpx

from app.ai import is_supported_speech_recognition_model, load_model_profiles
from app.config import settings
from app.services.model_call_logs import record_business_model_call


ASR_MAX_ATTEMPTS = 3
ASR_RETRYABLE_STATUS_CODES = {429, 500, 502, 503, 504}


def _chat_endpoint(base_url: str) -> str:
    clean = base_url.rstrip("/")
    return (
        f"{clean}/chat/completions"
        if clean.endswith("/v1")
        else f"{clean}/v1/chat/completions"
    )


def _prepare_asr_data_uri(audio_path: Path) -> str:
    probe = subprocess.run(
        [settings.ffprobe_binary, "-v", "error", "-show_entries", "format=duration", "-of", "default=nw=1:nk=1", str(audio_path)],
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=120,
    )
    try:
        duration = float(probe.stdout.decode("utf-8").strip())
    except ValueError as exc:
        raise RuntimeError("无法读取待识别音频的时长") from exc
    if probe.returncode != 0 or duration <= 0:
        raise RuntimeError("无法读取待识别音频的时长")
    if duration > 300:
        raise ValueError("音频超过 qwen3-asr-flash 的5分钟限制，请缩短后重试")
    with tempfile.TemporaryDirectory(prefix="codexwork-asr-") as temporary_root:
        prepared = Path(temporary_root) / "input.mp3"
        result = subprocess.run(
            [
                settings.ffmpeg_binary,
                "-v", "error", "-y", "-i", str(audio_path),
                "-vn", "-ac", "1", "-ar", "16000", "-b:a", "64k", str(prepared),
            ],
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=600,
        )
        if result.returncode != 0 or not prepared.is_file():
            detail = result.stderr.decode("utf-8", errors="replace")[-500:]
            raise RuntimeError(detail or "FFmpeg 无法准备语音识别音频")
        if prepared.stat().st_size > 10 * 1024 * 1024:
            raise ValueError("音频超过 qwen3-asr-flash 的 10MB 限制，请使用不超过5分钟的音频")
        encoded = base64.b64encode(prepared.read_bytes()).decode("ascii")
    return f"data:audio/mpeg;base64,{encoded}"


def _response_error(response: httpx.Response) -> tuple[str, str]:
    response_text = response.text.strip()
    request_id = ""
    try:
        payload = response.json()
        if isinstance(payload, dict):
            request_id = str(payload.get("request_id") or "").strip()
    except ValueError:
        pass
    message = f"HTTP {response.status_code}: {response_text[:1000] or response.reason_phrase}"
    return message, request_id


def _is_retryable_error(exc: Exception) -> bool:
    if isinstance(exc, httpx.HTTPStatusError):
        return exc.response.status_code in ASR_RETRYABLE_STATUS_CODES
    return isinstance(exc, (httpx.TimeoutException, httpx.NetworkError))


def recognize_narration_audio(
    audio_path: Path,
    *,
    approved_text: str = "",
    call_id: str = "",
    business_step: str = "音频转文案",
) -> dict[str, Any]:
    profile = next(
        (
            item
            for item in load_model_profiles(include_api_key=True)
            if item.stage == "speech_recognition"
        ),
        None,
    )
    if (
        profile is None
        or not profile.base_url
        or not profile.model
        or not profile.api_key
    ):
        raise ValueError("请先在模型配置中完整配置“音频转文案”模型")
    started = time.monotonic()
    attempt_number = 1
    provider_request_id = ""
    try:
        if not is_supported_speech_recognition_model(profile.model):
            raise ValueError(
                "当前音频转文案只支持非实时 qwen3-asr-flash 模型；"
                "不能使用带 realtime 或 filetrans 的模型"
            )
        data_uri = _prepare_asr_data_uri(audio_path)
        messages: list[dict[str, Any]] = []
        if approved_text.strip():
            messages.append({"role": "system", "content": [{"type": "text", "text": approved_text.strip()}]})
        messages.append({
            "role": "user",
            "content": [{"type": "input_audio", "input_audio": {"data": data_uri}}],
        })
        request_payload = {
            "model": profile.model,
            "messages": messages,
            "stream": False,
            "asr_options": {"enable_itn": True},
        }
        for attempt_number in range(1, ASR_MAX_ATTEMPTS + 1):
            attempt_started = time.monotonic()
            try:
                response = httpx.post(
                    _chat_endpoint(profile.base_url),
                    headers={"Authorization": f"Bearer {profile.api_key.strip()}"},
                    json=request_payload,
                    timeout=180,
                    proxy=profile.proxy_url or None,
                )
                response.raise_for_status()
                break
            except Exception as exc:
                retryable = _is_retryable_error(exc)
                if isinstance(exc, httpx.HTTPStatusError):
                    message, provider_request_id = _response_error(exc.response)
                else:
                    message = str(exc)
                    provider_request_id = ""
                if not retryable or attempt_number >= ASR_MAX_ATTEMPTS:
                    raise
                record_business_model_call(
                    stage=profile.stage,
                    label=profile.label,
                    provider="bailian",
                    model=profile.model,
                    input_payload={"audio_path": str(audio_path)},
                    output_payload={
                        "error": message,
                        "provider_request_id": provider_request_id,
                        "will_retry": True,
                    },
                    success=False,
                    duration_ms=int((time.monotonic() - attempt_started) * 1000),
                    business_step=business_step,
                    call_id=call_id,
                    attempt_number=attempt_number,
                )
                time.sleep(attempt_number)
        payload = response.json()
        provider_request_id = str(payload.get("request_id") or "") if isinstance(payload, dict) else ""
        choices = payload.get("choices") or []
        message = choices[0].get("message") if choices and isinstance(choices[0], dict) else {}
        text = str((message or {}).get("content") or "").strip()
        cues: list[dict[str, Any]] = []
        if not text:
            raise RuntimeError("音频转文案模型未返回有效文字")
        duration_ms = int((time.monotonic() - started) * 1000)
        record_business_model_call(
            stage=profile.stage,
            label=profile.label,
            provider="bailian",
            model=profile.model,
            input_payload={
                "audio_path": str(audio_path),
                "approved_text_supplied": bool(approved_text.strip()),
            },
            output_payload={
                "text": text,
                "segments": cues,
                "provider_request_id": provider_request_id,
            },
            success=True,
            duration_ms=duration_ms,
            business_step=business_step,
            call_id=call_id,
            attempt_number=attempt_number,
        )
        return {"text": text, "cues": cues, "model": profile.model}
    except Exception as exc:
        if isinstance(exc, httpx.HTTPStatusError):
            message, provider_request_id = _response_error(exc.response)
        else:
            message = str(exc)
        record_business_model_call(
            stage=profile.stage,
            label=profile.label,
            provider="bailian",
            model=profile.model,
            input_payload={"audio_path": str(audio_path)},
            output_payload={
                "error": message,
                "provider_request_id": provider_request_id,
                "will_retry": False,
            },
            success=False,
            duration_ms=int((time.monotonic() - started) * 1000),
            business_step=business_step,
            call_id=call_id,
            attempt_number=attempt_number,
        )
        raise RuntimeError(f"音频转文案失败：{message}") from exc
