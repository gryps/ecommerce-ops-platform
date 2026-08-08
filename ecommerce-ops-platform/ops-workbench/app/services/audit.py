from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.domain.models import AuditEvent


def record_audit(
    session: Session,
    *,
    actor_id: str | None,
    action: str,
    object_type: str,
    object_id: str,
    before: dict[str, Any] | None = None,
    after: dict[str, Any] | None = None,
    reason: str = "",
) -> AuditEvent:
    event = AuditEvent(
        actor_id=actor_id,
        action=action,
        object_type=object_type,
        object_id=object_id,
        before=before or {},
        after=after or {},
        reason=reason,
    )
    session.add(event)
    return event
