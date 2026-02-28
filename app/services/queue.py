from __future__ import annotations

import uuid
from collections import deque
from dataclasses import dataclass
from datetime import datetime


@dataclass
class QueueEntry:
    session_track_id: uuid.UUID
    track_id: uuid.UUID
    added_by_member_id: uuid.UUID
    added_at: datetime
    score: int
    status: str


def rank_queue(
    entries: list[QueueEntry],
    fairness_enabled: bool = True,
    cooldown_songs: int = 1,
) -> list[QueueEntry]:
    """
    Pure ranking function — no DB calls.

    Sorting rules:
      1. Higher score first
      2. Earlier added_at as tiebreaker

    Fairness (when enabled):
      Prevent the same member from occupying consecutive positions within
      a rolling window of `cooldown_songs` slots.
      Deferred tracks are appended after all non-deferred tracks.
    """
    queued = [e for e in entries if e.status == "QUEUED"]
    sorted_entries = sorted(queued, key=lambda e: (-e.score, e.added_at))

    if not fairness_enabled or cooldown_songs < 1:
        return sorted_entries

    result: list[QueueEntry] = []
    deferred: list[QueueEntry] = []
    recent_members: deque[uuid.UUID] = deque(maxlen=cooldown_songs)

    for entry in sorted_entries:
        if entry.added_by_member_id not in recent_members:
            result.append(entry)
            recent_members.append(entry.added_by_member_id)
        else:
            deferred.append(entry)

    # Append deferred tracks (preserving their relative score order)
    return result + deferred
