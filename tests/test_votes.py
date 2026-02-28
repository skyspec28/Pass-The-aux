"""
Integration tests for vote uniqueness and idempotency.
Requires a running Postgres instance (see conftest.py).
"""
import pytest
import pytest_asyncio

from app.models.session import Session, SessionMember
from app.models.track import SessionTrack, Track
from app.models.vote import Vote


@pytest_asyncio.fixture
async def seeded(db):
    """Seed a minimal session, member, track, and session_track."""
    import uuid

    session = Session(code="TESTVT1", title="Vote Test", status="ACTIVE", settings={})
    db.add(session)
    await db.flush()

    member = SessionMember(session_id=session.id, display_name="Voter", role="HOST")
    db.add(member)
    await db.flush()

    track = Track(provider="YOUTUBE", provider_track_id="dQw4w9WgXcQ")
    db.add(track)
    await db.flush()

    st = SessionTrack(session_id=session.id, track_id=track.id, added_by_member_id=member.id)
    db.add(st)
    await db.flush()

    return {"session": session, "member": member, "track": track, "session_track": st}


@pytest.mark.asyncio
async def test_single_vote_inserted(db, seeded):
    st = seeded["session_track"]
    member = seeded["member"]

    vote = Vote(session_track_id=st.id, member_id=member.id, value=1)
    db.add(vote)
    await db.flush()

    from sqlalchemy import select
    result = await db.execute(select(Vote).where(Vote.session_track_id == st.id))
    votes = result.scalars().all()
    assert len(votes) == 1
    assert votes[0].value == 1


@pytest.mark.asyncio
async def test_duplicate_vote_raises_integrity_error(db, seeded):
    """Two votes from the same member on the same track should violate the unique constraint."""
    from sqlalchemy.exc import IntegrityError

    st = seeded["session_track"]
    member = seeded["member"]

    db.add(Vote(session_track_id=st.id, member_id=member.id, value=1))
    await db.flush()
    db.add(Vote(session_track_id=st.id, member_id=member.id, value=-1))

    with pytest.raises(IntegrityError):
        await db.flush()


@pytest.mark.asyncio
async def test_different_members_can_both_vote(db, seeded):
    session = seeded["session"]
    st = seeded["session_track"]
    member1 = seeded["member"]

    member2 = SessionMember(session_id=session.id, display_name="Voter2", role="GUEST")
    db.add(member2)
    await db.flush()

    db.add(Vote(session_track_id=st.id, member_id=member1.id, value=1))
    db.add(Vote(session_track_id=st.id, member_id=member2.id, value=1))
    await db.flush()

    from sqlalchemy import select, func
    result = await db.execute(
        select(func.sum(Vote.value)).where(Vote.session_track_id == st.id)
    )
    assert result.scalar_one() == 2


@pytest.mark.asyncio
async def test_vote_value_constraint(db, seeded):
    """Value must be +1 or -1; 0 should violate the check constraint."""
    from sqlalchemy.exc import IntegrityError

    st = seeded["session_track"]
    member = seeded["member"]

    db.add(Vote(session_track_id=st.id, member_id=member.id, value=0))
    with pytest.raises(IntegrityError):
        await db.flush()
