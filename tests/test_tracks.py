"""
Integration tests for the track add flow.
Requires a running Postgres instance (see conftest.py).
"""
import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, patch

from app.services.url_parser import parse_track_url


class TestUrlParser:
    """Unit tests for URL parsing — no DB or network required."""

    def test_spotify_track_url(self):
        result = parse_track_url("https://open.spotify.com/track/4iV5W9uYEdYUVa79Axb7Rh")
        assert result == ("SPOTIFY", "4iV5W9uYEdYUVa79Axb7Rh")

    def test_spotify_url_with_query_params(self):
        result = parse_track_url("https://open.spotify.com/track/4iV5W9uYEdYUVa79Axb7Rh?si=abc123")
        assert result == ("SPOTIFY", "4iV5W9uYEdYUVa79Axb7Rh")

    def test_youtube_watch_url(self):
        result = parse_track_url("https://www.youtube.com/watch?v=dQw4w9WgXcQ")
        assert result == ("YOUTUBE", "dQw4w9WgXcQ")

    def test_youtube_short_url(self):
        result = parse_track_url("https://youtu.be/dQw4w9WgXcQ")
        assert result == ("YOUTUBE", "dQw4w9WgXcQ")

    def test_apple_music_url(self):
        result = parse_track_url("https://music.apple.com/us/album/blinding-lights/1499378108?i=1499378615")
        assert result == ("APPLE", "1499378615")

    def test_unknown_url_returns_none(self):
        result = parse_track_url("https://soundcloud.com/artist/track")
        assert result is None

    def test_invalid_url_returns_none(self):
        result = parse_track_url("not-a-url")
        assert result is None


@pytest.mark.asyncio
async def test_add_track_creates_session_track(db):
    """Verify SessionTrack is created when a track is added to a session."""
    from app.models.session import Session, SessionMember
    from app.models.track import SessionTrack, Track
    from sqlalchemy import select

    # Seed
    session = Session(code="TRKADD1", title="Track Test", status="ACTIVE", settings={"dedupe_tracks": False})
    db.add(session)
    await db.flush()

    member = SessionMember(session_id=session.id, display_name="Adder", role="HOST")
    db.add(member)
    await db.flush()

    track = Track(provider="SPOTIFY", provider_track_id="abc123", metadata_status="PENDING")
    db.add(track)
    await db.flush()

    st = SessionTrack(session_id=session.id, track_id=track.id, added_by_member_id=member.id)
    db.add(st)
    await db.flush()

    result = await db.execute(
        select(SessionTrack).where(SessionTrack.session_id == session.id)
    )
    rows = result.scalars().all()
    assert len(rows) == 1
    assert rows[0].track_id == track.id
    assert rows[0].status == "QUEUED"


@pytest.mark.asyncio
async def test_dedupe_prevents_second_add(db):
    """Adding the same track twice to a session (same provider+id) should only create one SessionTrack."""
    from app.models.session import Session, SessionMember
    from app.models.track import SessionTrack, Track
    from sqlalchemy import select
    from sqlalchemy.exc import IntegrityError

    session = Session(code="DEDUPE01", title="Dedupe Test", status="ACTIVE", settings={"dedupe_tracks": True})
    db.add(session)
    await db.flush()

    member = SessionMember(session_id=session.id, display_name="Host", role="HOST")
    db.add(member)
    await db.flush()

    track = Track(provider="YOUTUBE", provider_track_id="uniqueid1")
    db.add(track)
    await db.flush()

    db.add(SessionTrack(session_id=session.id, track_id=track.id, added_by_member_id=member.id))
    await db.flush()

    db.add(SessionTrack(session_id=session.id, track_id=track.id, added_by_member_id=member.id))
    with pytest.raises(IntegrityError):
        await db.flush()
