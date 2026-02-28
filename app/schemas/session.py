from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class SessionSettings(BaseModel):
    allow_guest_add: bool = True
    allow_downvotes: bool = True
    max_adds_per_guest_per_10min: int = 3
    max_votes_per_guest_per_min: int = 12
    dedupe_tracks: bool = True
    explicit_filter: str = "ALLOW"  # ALLOW | BLOCK | HOST_ONLY
    fairness: dict[str, Any] = Field(default_factory=lambda: {"enabled": True, "cooldown_songs": 1})


class SessionCreate(BaseModel):
    title: str = Field(min_length=1, max_length=100)


class SessionCreateResponse(BaseModel):
    session_id: uuid.UUID
    code: str
    host_token: str


class SessionJoin(BaseModel):
    display_name: str = Field(min_length=1, max_length=40)


class SessionJoinResponse(BaseModel):
    member_id: uuid.UUID
    member_token: str
    role: str


class SessionOut(BaseModel):
    id: uuid.UUID
    code: str
    title: str
    status: str
    settings: dict[str, Any]
    created_at: datetime
    ended_at: datetime | None

    model_config = {"from_attributes": True}


class SettingsUpdate(BaseModel):
    settings: dict[str, Any]
