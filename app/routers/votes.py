from typing import Annotated

import structlog
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_redis, require_member_in_session
from app.models.session import Session, SessionMember
from app.models.track import SessionTrack
from app.models.vote import Vote
from app.schemas.vote import VoteRequest, VoteOut
from app.services.broadcast import manager
from app.services.ratelimit import check_rate_limit
from app.routers.tracks import build_queue_snapshot

router = APIRouter(tags=["votes"])
logger = structlog.get_logger()


@router.post("/sessions/{code}/tracks/{session_track_id}/vote", response_model=VoteOut, status_code=status.HTTP_201_CREATED)
async def cast_vote(
    code: str,
    session_track_id: str,
    body: VoteRequest,
    pair: Annotated[tuple[SessionMember, Session], Depends(require_member_in_session)],
    db: Annotated[AsyncSession, Depends(get_db)],
    redis=Depends(get_redis),
):
    member, session = pair
    sess_settings = session.settings or {}

    if body.value not in (1, -1):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Vote value must be 1 or -1")
    if body.value == -1 and not sess_settings.get("allow_downvotes", True):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Downvotes are disabled")

    # Rate limit
    allowed = await check_rate_limit(
        redis,
        key=f"rl:votes:{member.id}",
        limit=sess_settings.get("max_votes_per_guest_per_min", 12),
        window_seconds=60,
    )
    if not allowed:
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="Vote rate limit exceeded")

    # Verify session_track belongs to this session
    st_result = await db.execute(
        select(SessionTrack).where(SessionTrack.id == session_track_id, SessionTrack.session_id == session.id)
    )
    st = st_result.scalar_one_or_none()
    if st is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Track not found in this session")
    if st.status != "QUEUED":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Can only vote on queued tracks")

    # Upsert vote (change value if already voted)
    existing = await db.execute(
        select(Vote).where(Vote.session_track_id == session_track_id, Vote.member_id == member.id)
    )
    vote = existing.scalar_one_or_none()
    if vote is not None:
        vote.value = body.value
    else:
        vote = Vote(session_track_id=st.id, member_id=member.id, value=body.value)
        db.add(vote)

    # Recompute score
    score_result = await db.execute(
        select(func.coalesce(func.sum(Vote.value), 0)).where(Vote.session_track_id == st.id)
    )
    # Flush to include the new/updated vote in the sum
    await db.flush()
    score_result2 = await db.execute(
        select(func.coalesce(func.sum(Vote.value), 0)).where(Vote.session_track_id == st.id)
    )
    new_score = score_result2.scalar_one()
    st.score_cached = new_score
    await db.commit()
    await db.refresh(vote)

    # Vote counts
    up_result = await db.execute(
        select(func.count()).where(Vote.session_track_id == st.id, Vote.value == 1)
    )
    down_result = await db.execute(
        select(func.count()).where(Vote.session_track_id == st.id, Vote.value == -1)
    )
    upvotes = up_result.scalar_one()
    downvotes = down_result.scalar_one()

    await manager.broadcast(session.id, "vote.updated", {
        "session_track_id": session_track_id,
        "score": new_score,
        "upvotes": upvotes,
        "downvotes": downvotes,
    })
    queue_snapshot = await build_queue_snapshot(db, session.id)
    await manager.broadcast(session.id, "queue.updated", {"queue": queue_snapshot})

    logger.info("vote.cast", session_track_id=session_track_id, member_id=str(member.id), value=body.value)
    return vote


@router.delete("/sessions/{code}/tracks/{session_track_id}/vote", status_code=status.HTTP_204_NO_CONTENT)
async def remove_vote(
    code: str,
    session_track_id: str,
    pair: Annotated[tuple[SessionMember, Session], Depends(require_member_in_session)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    member, session = pair

    existing = await db.execute(
        select(Vote).where(Vote.session_track_id == session_track_id, Vote.member_id == member.id)
    )
    vote = existing.scalar_one_or_none()
    if vote is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No vote found")

    db.delete(vote)

    st_result = await db.execute(select(SessionTrack).where(SessionTrack.id == session_track_id))
    st = st_result.scalar_one_or_none()
    if st:
        await db.flush()
        score_result = await db.execute(
            select(func.coalesce(func.sum(Vote.value), 0)).where(Vote.session_track_id == st.id)
        )
        st.score_cached = score_result.scalar_one()

    await db.commit()

    queue_snapshot = await build_queue_snapshot(db, session.id)
    await manager.broadcast(session.id, "queue.updated", {"queue": queue_snapshot})
