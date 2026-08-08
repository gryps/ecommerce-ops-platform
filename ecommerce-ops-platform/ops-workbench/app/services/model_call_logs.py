from __future__ import annotations

import base64
import hashlib
import logging
import re
import uuid
from contextlib import contextmanager
from contextvars import ContextVar
from datetime import date, datetime, timedelta, timezone
from typing import Any, Iterator
from zoneinfo import ZoneInfo

from sqlalchemy import delete, func, select

from app.core.database import session_scope
from app.core.security import utc_now
from app.domain.models import ModelCallDailySummary, ModelCallLog


LOGGER = logging.getLogger(__name__)
LOCAL_TIMEZONE = ZoneInfo("Asia/Shanghai")
DETAIL_RETENTION_DAYS = 3
SENSITIVE_KEYS = {
    "api_key",
    "apikey",
    "api_secret",
    "secret",
    "password",
    "authorization",
    "access_token",
    "refresh_token",
    "token",
}
EMAIL_PATTERN = re.compile(r"(?<![\w.-])[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}(?![\w.-])")
PHONE_PATTERN = re.compile(r"(?<!\d)(?:\+?86[- ]?)?1[3-9]\d{9}(?!\d)")
BEARER_PATTERN = re.compile(r"(?i)\bBearer\s+[A-Za-z0-9._~+/=-]{8,}")
API_KEY_PATTERN = re.compile(r"\b(?:sk|ak)-[A-Za-z0-9_-]{8,}\b", re.IGNORECASE)
DATA_URL_PATTERN = re.compile(
    r"^data:([^;,]+)?(?:;[^,]*)?;base64,(.+)$",
    re.DOTALL,
)
BASE64_PATTERN = re.compile(r"^[A-Za-z0-9+/=_\s-]+$")
_business_context: ContextVar[dict[str, Any]] = ContextVar(
    "model_business_context",
    default={},
)
_last_cleanup_date: date | None = None


@contextmanager
def model_business_context(
    *,
    business_step: str,
    objects: list[dict[str, Any]] | None = None,
    call_id: str = "",
    attempt_number: int = 1,
) -> Iterator[None]:
    token = _business_context.set(
        {
            "business_step": business_step,
            "objects": objects or [],
            "call_id": call_id,
            "attempt_number": max(1, int(attempt_number)),
        }
    )
    try:
        yield
    finally:
        _business_context.reset(token)


def current_model_business_context() -> dict[str, Any]:
    return dict(_business_context.get())


def _binary_metadata(raw: bytes, content_type: str = "application/octet-stream") -> dict:
    return {
        "binary_omitted": True,
        "content_type": content_type or "application/octet-stream",
        "byte_size": len(raw),
        "sha256": hashlib.sha256(raw).hexdigest(),
    }


def _sanitize_string(value: str) -> Any:
    match = DATA_URL_PATTERN.match(value)
    if match:
        try:
            raw = base64.b64decode(match.group(2), validate=False)
        except Exception:
            raw = b""
        return _binary_metadata(raw, match.group(1) or "application/octet-stream")
    compact = "".join(value.split())
    if len(compact) >= 512 and BASE64_PATTERN.fullmatch(compact):
        try:
            raw = base64.b64decode(compact, validate=False)
        except Exception:
            raw = b""
        return _binary_metadata(raw)
    redacted = BEARER_PATTERN.sub("Bearer [已脱敏]", value)
    redacted = API_KEY_PATTERN.sub("[API Key 已脱敏]", redacted)
    redacted = EMAIL_PATTERN.sub("[邮箱已脱敏]", redacted)
    redacted = PHONE_PATTERN.sub("[手机号已脱敏]", redacted)
    return redacted


def sanitize_model_payload(value: Any, key: str = "") -> Any:
    if key.casefold() in SENSITIVE_KEYS:
        return "[已脱敏]"
    if isinstance(value, bytes):
        return _binary_metadata(value)
    if isinstance(value, str):
        return _sanitize_string(value)
    if isinstance(value, dict):
        sanitized = {}
        for item_key, item_value in value.items():
            normalized_key = str(item_key)
            sanitized[normalized_key] = sanitize_model_payload(
                item_value, normalized_key
            )
        return sanitized
    if isinstance(value, (list, tuple)):
        return [sanitize_model_payload(item) for item in value]
    if value is None or isinstance(value, (bool, int, float)):
        return value
    return _sanitize_string(str(value))


def _local_stat_date(created_at: datetime | None = None) -> date:
    moment = created_at or utc_now()
    if moment.tzinfo is None:
        moment = moment.replace(tzinfo=timezone.utc)
    return moment.astimezone(LOCAL_TIMEZONE).date()


def record_business_model_call(
    *,
    stage: str,
    label: str,
    provider: str,
    model: str,
    input_payload: Any,
    output_payload: Any,
    success: bool,
    duration_ms: int,
    usage: dict[str, Any] | None = None,
    business_step: str = "",
    business_objects: list[dict[str, Any]] | None = None,
    call_id: str = "",
    attempt_number: int | None = None,
) -> None:
    """Write detail and permanent aggregate in an independent best-effort transaction."""
    context = current_model_business_context()
    objects = business_objects if business_objects is not None else context.get("objects", [])
    step = business_step or str(context.get("business_step") or stage)
    usage = usage if isinstance(usage, dict) else {}
    reported = any(
        key in usage
        for key in ("prompt_tokens", "completion_tokens", "total_tokens")
    )
    input_tokens = int(usage.get("prompt_tokens") or 0) if reported else None
    output_tokens = int(usage.get("completion_tokens") or 0) if reported else None
    total_tokens = int(usage.get("total_tokens") or 0) if reported else None
    created_at = utc_now()
    try:
        with session_scope() as session:
            session.add(
                ModelCallLog(
                    call_id=call_id or str(context.get("call_id") or "") or uuid.uuid4().hex,
                    attempt_number=max(
                        1,
                        int(
                            attempt_number
                            if attempt_number is not None
                            else context.get("attempt_number") or 1
                        ),
                    ),
                    stage=stage,
                    label=label,
                    provider=provider,
                    model=model,
                    business_step=step,
                    business_objects=sanitize_model_payload(objects),
                    input_payload={"request": sanitize_model_payload(input_payload)},
                    output_payload={"response": sanitize_model_payload(output_payload)},
                    success=success,
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                    total_tokens=total_tokens,
                    token_usage_reported=reported,
                    duration_ms=max(0, int(duration_ms)),
                    created_at=created_at,
                )
            )
            stat_date = _local_stat_date(created_at)
            summary = session.scalar(
                select(ModelCallDailySummary).where(
                    ModelCallDailySummary.stat_date == stat_date,
                    ModelCallDailySummary.stage == stage,
                )
            )
            if summary is None:
                summary = ModelCallDailySummary(
                    stat_date=stat_date,
                    stage=stage,
                    successful_calls=0,
                    failed_calls=0,
                    input_tokens=0,
                    output_tokens=0,
                    total_tokens=0,
                    token_reported_calls=0,
                    total_duration_ms=0,
                    updated_at=created_at,
                )
                session.add(summary)
            summary.successful_calls += 1 if success else 0
            summary.failed_calls += 0 if success else 1
            summary.input_tokens += input_tokens or 0
            summary.output_tokens += output_tokens or 0
            summary.total_tokens += total_tokens or 0
            summary.token_reported_calls += 1 if reported else 0
            summary.total_duration_ms += max(0, int(duration_ms))
            summary.updated_at = created_at
    except Exception:
        LOGGER.exception("业务模型调用日志写入失败，原业务继续执行")
    maybe_cleanup_expired_model_call_logs()


def cleanup_expired_model_call_logs(now: datetime | None = None) -> int:
    moment = now or utc_now()
    cutoff = moment - timedelta(days=DETAIL_RETENTION_DAYS)
    with session_scope() as session:
        result = session.execute(
            delete(ModelCallLog).where(ModelCallLog.created_at < cutoff)
        )
        return int(result.rowcount or 0)


def maybe_cleanup_expired_model_call_logs(now: datetime | None = None) -> int:
    global _last_cleanup_date
    current_date = _local_stat_date(now)
    if _last_cleanup_date == current_date:
        return 0
    try:
        deleted = cleanup_expired_model_call_logs(now)
    except Exception:
        LOGGER.exception("过期业务模型调用日志清理失败")
        return 0
    _last_cleanup_date = current_date
    return deleted


def _summary_values(rows: list[ModelCallDailySummary]) -> dict[str, Any]:
    successful = sum(row.successful_calls for row in rows)
    failed = sum(row.failed_calls for row in rows)
    calls = successful + failed
    duration = sum(row.total_duration_ms for row in rows)
    return {
        "calls": calls,
        "successful_calls": successful,
        "failed_calls": failed,
        "input_tokens": sum(row.input_tokens for row in rows),
        "output_tokens": sum(row.output_tokens for row in rows),
        "total_tokens": sum(row.total_tokens for row in rows),
        "token_reported_calls": sum(row.token_reported_calls for row in rows),
        "average_duration_ms": round(duration / calls) if calls else 0,
    }


def _log_list_item(row: ModelCallLog) -> dict[str, Any]:
    return {
        "id": row.id,
        "call_id": row.call_id,
        "attempt_number": row.attempt_number,
        "stage": row.stage,
        "label": row.label,
        "model": row.model,
        "business_step": row.business_step,
        "business_objects": row.business_objects,
        "success": row.success,
        "input_tokens": row.input_tokens,
        "output_tokens": row.output_tokens,
        "total_tokens": row.total_tokens,
        "token_usage_reported": row.token_usage_reported,
        "duration_ms": row.duration_ms,
        "created_at": row.created_at,
    }


def model_call_summary(stage: str) -> dict[str, Any]:
    maybe_cleanup_expired_model_call_logs()
    today = _local_stat_date()
    first_day = today - timedelta(days=6)
    with session_scope() as session:
        rows = session.scalars(
            select(ModelCallDailySummary)
            .where(ModelCallDailySummary.stage == stage)
            .order_by(ModelCallDailySummary.stat_date)
        ).all()
        recent = session.scalars(
            select(ModelCallLog)
            .where(ModelCallLog.stage == stage)
            .order_by(ModelCallLog.created_at.desc())
            .limit(5)
        ).all()
    by_date = {row.stat_date: row for row in rows}
    trend = []
    for offset in range(7):
        stat_date = first_day + timedelta(days=offset)
        values = _summary_values([by_date[stat_date]] if stat_date in by_date else [])
        trend.append({"date": stat_date, **values})
    return {
        "stage": stage,
        "today": _summary_values([row for row in rows if row.stat_date == today]),
        "last_7_days": _summary_values(
            [row for row in rows if first_day <= row.stat_date <= today]
        ),
        "all_time": _summary_values(rows),
        "trend": trend,
        "recent_logs": [_log_list_item(row) for row in recent],
    }


def model_call_log_page(stage: str, page: int, page_size: int = 10) -> dict[str, Any]:
    maybe_cleanup_expired_model_call_logs()
    page = max(1, page)
    page_size = 10
    with session_scope() as session:
        total = int(
            session.scalar(
                select(func.count(ModelCallLog.id)).where(ModelCallLog.stage == stage)
            )
            or 0
        )
        rows = session.scalars(
            select(ModelCallLog)
            .where(ModelCallLog.stage == stage)
            .order_by(ModelCallLog.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        ).all()
    return {
        "items": [_log_list_item(row) for row in rows],
        "page": page,
        "page_size": page_size,
        "total": total,
        "total_pages": max(1, (total + page_size - 1) // page_size),
    }


def model_call_log_detail(stage: str, log_id: str) -> dict[str, Any]:
    with session_scope() as session:
        row = session.get(ModelCallLog, log_id)
        if row is None or row.stage != stage:
            raise LookupError("模型调用日志不存在或已超过 3 天保留期")
        return {
            **_log_list_item(row),
            "provider": row.provider,
            "input_payload": row.input_payload,
            "output_payload": row.output_payload,
        }


def clear_model_call_logs(stage: str) -> int:
    with session_scope() as session:
        result = session.execute(
            delete(ModelCallLog).where(ModelCallLog.stage == stage)
        )
        return int(result.rowcount or 0)
