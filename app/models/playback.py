from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Integer, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.track import SessionTrack


class PlaybackState(Base):
    __tablename__ = "playback_states"

    session_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("sessions.id", ondelete="CASCADE"), primary_key=True)
    current_session_track_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("session_tracks.id"), nullable=True)
    state: Mapped[str] = mapped_column(String(10), nullable=False, default="STOPPED")  # PLAYING | PAUSED | STOPPED
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    position_ms: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    current_track: Mapped[SessionTrack | None] = relationship("SessionTrack", foreign_keys=[current_session_track_id])
