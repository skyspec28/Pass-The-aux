from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, SmallInteger, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.session import SessionMember
    from app.models.track import SessionTrack


class Vote(Base):
    __tablename__ = "votes"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_track_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("session_tracks.id", ondelete="CASCADE"), nullable=False)
    member_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("session_members.id"), nullable=False)
    value: Mapped[int] = mapped_column(SmallInteger, nullable=False)  # +1 or -1
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    session_track: Mapped[SessionTrack] = relationship("SessionTrack", back_populates="votes")
    member: Mapped[SessionMember] = relationship("SessionMember")

    __table_args__ = (
        UniqueConstraint("session_track_id", "member_id", name="uq_votes_member_track"),
        CheckConstraint("value IN (1, -1)", name="ck_votes_value"),
    )
