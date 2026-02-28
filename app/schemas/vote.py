from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel


class VoteRequest(BaseModel):
    value: int  # 1 or -1


class VoteOut(BaseModel):
    id: uuid.UUID
    session_track_id: uuid.UUID
    member_id: uuid.UUID
    value: int
    created_at: datetime

    model_config = {"from_attributes": True}


class VoteUpdatedData(BaseModel):
    session_track_id: uuid.UUID
    score: int
    upvotes: int
    downvotes: int
