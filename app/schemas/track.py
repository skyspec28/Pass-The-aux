from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel


class TrackAddRequest(BaseModel):
    # Either provider+id OR a raw URL
    provider: str | None = None     # SPOTIFY | APPLE | YOUTUBE
    provider_track_id: str | None = None
    url: str | None = None


class TrackOut(BaseModel):
    id: uuid.UUID
    provider: str
    provider_track_id: str
    title: str | None
    artist: str | None
    duration_ms: int | None
    artwork_url: str | None
    explicit: bool | None
    source_url: str | None
    metadata_status: str

    model_config = {"from_attributes": True}


class SessionTrackOut(BaseModel):
    id: uuid.UUID
    session_id: uuid.UUID
    track_id: uuid.UUID
    added_by_member_id: uuid.UUID
    added_at: datetime
    status: str
    score_cached: int
    track: TrackOut

    model_config = {"from_attributes": True}
