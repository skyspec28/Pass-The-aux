from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel


class PlaybackOut(BaseModel):
    session_id: uuid.UUID
    current_session_track_id: uuid.UUID | None
    state: str
    started_at: datetime | None
    position_ms: int
    updated_at: datetime

    model_config = {"from_attributes": True}


class SeekRequest(BaseModel):
    position_ms: int
