from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.session import Session, SessionMember
    from app.models.vote import Vote


class Track(Base):
    __tablename__ = "tracks"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    provider: Mapped[str] = mapped_column(String(10), nullable=False)  # SPOTIFY | APPLE | YOUTUBE
    provider_track_id: Mapped[str] = mapped_column(Text, nullable=False)
    title: Mapped[str | None] = mapped_column(Text, nullable=True)
    artist: Mapped[str | None] = mapped_column(Text, nullable=True)
    duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    artwork_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    explicit: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    source_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    metadata_status: Mapped[str] = mapped_column(String(10), nullable=False, default="PENDING")

    session_tracks: Mapped[list[SessionTrack]] = relationship("SessionTrack", back_populates="track", lazy="select")

    __table_args__ = (
        UniqueConstraint("provider", "provider_track_id", name="uq_tracks_provider_id"),
    )


class SessionTrack(Base):
    __tablename__ = "session_tracks"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False)
    track_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("tracks.id"), nullable=False)
    added_by_member_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("session_members.id"), nullable=False)
    added_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    status: Mapped[str] = mapped_column(String(10), nullable=False, default="QUEUED")
    score_cached: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    session: Mapped[Session] = relationship("Session", back_populates="session_tracks")
    track: Mapped[Track] = relationship("Track", back_populates="session_tracks")
    added_by: Mapped[SessionMember] = relationship("SessionMember", foreign_keys=[added_by_member_id])
    votes: Mapped[list[Vote]] = relationship("Vote", back_populates="session_track", lazy="select")

    __table_args__ = (
        UniqueConstraint("session_id", "track_id", name="uq_session_tracks_dedup"),
    )
