"""Helpers for writing to the Event audit table."""
from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.event import Event


async def audit(
    db: AsyncSession,
    session_id: uuid.UUID,
    event_type: str,
    payload: dict[str, Any] | None = None,
) -> None:
    """Insert an audit event record. Fire-and-forget — does not commit."""
    db.add(Event(session_id=session_id, type=event_type, payload=payload or {}))
