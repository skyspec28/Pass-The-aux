from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel


class MemberOut(BaseModel):
    id: uuid.UUID
    session_id: uuid.UUID
    display_name: str
    role: str
    is_banned: bool
    muted_until: datetime | None
    joined_at: datetime

    model_config = {"from_attributes": True}


class MuteRequest(BaseModel):
    seconds: int
