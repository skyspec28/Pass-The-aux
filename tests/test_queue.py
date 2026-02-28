"""Unit tests for the queue ranking algorithm (no DB required)."""
import uuid
from datetime import datetime, timedelta, timezone

import pytest

from app.services.queue import QueueEntry, rank_queue


_BASE_TIME = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)


def _entry(member_id: uuid.UUID, score: int, seconds_ago: int = 0) -> QueueEntry:
    return QueueEntry(
        session_track_id=uuid.uuid4(),
        track_id=uuid.uuid4(),
        added_by_member_id=member_id,
        added_at=_BASE_TIME - timedelta(seconds=seconds_ago),
        score=score,
        status="QUEUED",
    )


ALICE = uuid.uuid4()
BOB = uuid.uuid4()
CAROL = uuid.uuid4()


class TestRankQueueBasic:
    def test_empty_returns_empty(self):
        assert rank_queue([]) == []

    def test_single_entry(self):
        e = _entry(ALICE, score=5)
        assert rank_queue([e]) == [e]

    def test_higher_score_first(self):
        low = _entry(ALICE, score=1)
        high = _entry(BOB, score=10)
        result = rank_queue([low, high], fairness_enabled=False)
        assert result[0] is high
        assert result[1] is low

    def test_tiebreak_by_earlier_added_at(self):
        earlier = _entry(ALICE, score=5, seconds_ago=10)
        later = _entry(BOB, score=5, seconds_ago=0)
        result = rank_queue([later, earlier], fairness_enabled=False)
        assert result[0] is earlier

    def test_non_queued_tracks_excluded(self):
        played = QueueEntry(
            session_track_id=uuid.uuid4(),
            track_id=uuid.uuid4(),
            added_by_member_id=ALICE,
            added_at=datetime(2024, 1, 1, tzinfo=timezone.utc),
            score=99,
            status="PLAYED",
        )
        queued = _entry(BOB, score=1)
        result = rank_queue([played, queued])
        assert len(result) == 1
        assert result[0] is queued


class TestFairness:
    def test_fairness_prevents_consecutive_same_member(self):
        """Alice's two high-scoring tracks should not be consecutive."""
        alice1 = _entry(ALICE, score=10, seconds_ago=20)
        alice2 = _entry(ALICE, score=9, seconds_ago=10)
        bob1 = _entry(BOB, score=8, seconds_ago=5)

        result = rank_queue([alice1, alice2, bob1], fairness_enabled=True, cooldown_songs=1)

        # alice1 first (highest), then bob1 (next different member), then alice2
        assert result[0] is alice1
        assert result[1] is bob1
        assert result[2] is alice2

    def test_fairness_disabled_respects_score_only(self):
        alice1 = _entry(ALICE, score=10)
        alice2 = _entry(ALICE, score=9)
        bob1 = _entry(BOB, score=8)

        result = rank_queue([alice1, alice2, bob1], fairness_enabled=False)
        assert result[0] is alice1
        assert result[1] is alice2
        assert result[2] is bob1

    def test_cooldown_2_blocks_two_slots(self):
        """With cooldown_songs=2, Alice can't appear within 2 positions of her last track."""
        alice1 = _entry(ALICE, score=10)
        alice2 = _entry(ALICE, score=7)
        bob1 = _entry(BOB, score=9)
        carol1 = _entry(CAROL, score=8)

        result = rank_queue([alice1, alice2, bob1, carol1], fairness_enabled=True, cooldown_songs=2)

        assert result[0] is alice1
        # Next two must not be ALICE
        assert result[1].added_by_member_id != ALICE
        assert result[2].added_by_member_id != ALICE

    def test_all_same_member_still_returns_all(self):
        """If only one member added tracks, all are returned (deferred order)."""
        e1 = _entry(ALICE, score=5)
        e2 = _entry(ALICE, score=3)
        e3 = _entry(ALICE, score=1)

        result = rank_queue([e1, e2, e3], fairness_enabled=True, cooldown_songs=1)
        assert len(result) == 3
        # e1 should still be first
        assert result[0] is e1
