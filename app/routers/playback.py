from datetime import datetime, timezone
from typing import Annotated

import structlog
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import require_host, require_member_in_session
from app.models.playback import PlaybackState
from app.models.session import Session, SessionMember
from app.models.track import SessionTrack
from app.schemas.playback import PlaybackOut, SeekRequest
from app.services.broadcast import manager

router = APIRouter(tags=["playback"])
logger = structlog.get_logger()


async def _get_or_create_playback(db: AsyncSession, session_id) -> PlaybackState:
    result = await db.execute(select(PlaybackState).where(PlaybackState.session_id == session_id))
    pb = result.scalar_one_or_none()
    if pb is None:
        pb = PlaybackState(session_id=session_id)
        db.add(pb)
        await db.commit()
        await db.refresh(pb)
    return pb


@router.get("/sessions/{code}/playback", response_model=PlaybackOut)
async def get_playback(
    code: str,
    pair: Annotated[tuple[SessionMember, Session], Depends(require_member_in_session)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    _, session = pair
    return await _get_or_create_playback(db, session.id)


@router.post("/sessions/{code}/playback/start", response_model=PlaybackOut)
async def start_playback(
    code: str,
    pair: Annotated[tuple[SessionMember, Session], Depends(require_host)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    _, session = pair
    pb = await _get_or_create_playback(db, session.id)

    if pb.state == "PLAYING":
        return pb

    # If no current track, pick the top queued track
    if pb.current_session_track_id is None:
        next_result = await db.execute(
            select(SessionTrack)
            .where(SessionTrack.session_id == session.id, SessionTrack.status == "QUEUED")
            .order_by(SessionTrack.score_cached.desc(), SessionTrack.added_at.asc())
            .limit(1)
        )
        next_track = next_result.scalar_one_or_none()
        if next_track:
            pb.current_session_track_id = next_track.id
            next_track.status = "PLAYING"

    pb.state = "PLAYING"
    pb.started_at = datetime.now(timezone.utc)
    pb.updated_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(pb)

    await manager.broadcast(session.id, "playback.updated", {
        "state": pb.state,
        "current_session_track_id": str(pb.current_session_track_id) if pb.current_session_track_id else None,
        "position_ms": pb.position_ms,
    })
    return pb


@router.post("/sessions/{code}/playback/pause", response_model=PlaybackOut)
async def pause_playback(
    code: str,
    pair: Annotated[tuple[SessionMember, Session], Depends(require_host)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    _, session = pair
    pb = await _get_or_create_playback(db, session.id)
    pb.state = "PAUSED"
    pb.updated_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(pb)

    await manager.broadcast(session.id, "playback.updated", {"state": pb.state, "position_ms": pb.position_ms})
    return pb


@router.post("/sessions/{code}/playback/next", response_model=PlaybackOut)
async def next_track(
    code: str,
    pair: Annotated[tuple[SessionMember, Session], Depends(require_host)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    _, session = pair
    pb = await _get_or_create_playback(db, session.id)

    # Mark current track as played
    if pb.current_session_track_id:
        curr_result = await db.execute(select(SessionTrack).where(SessionTrack.id == pb.current_session_track_id))
        curr = curr_result.scalar_one_or_none()
        if curr:
            curr.status = "PLAYED"

    # Pick next
    next_result = await db.execute(
        select(SessionTrack)
        .where(SessionTrack.session_id == session.id, SessionTrack.status == "QUEUED")
        .order_by(SessionTrack.score_cached.desc(), SessionTrack.added_at.asc())
        .limit(1)
    )
    next_track_row = next_result.scalar_one_or_none()

    if next_track_row:
        pb.current_session_track_id = next_track_row.id
        next_track_row.status = "PLAYING"
        pb.state = "PLAYING"
    else:
        pb.current_session_track_id = None
        pb.state = "STOPPED"

    pb.position_ms = 0
    pb.started_at = datetime.now(timezone.utc)
    pb.updated_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(pb)

    await manager.broadcast(session.id, "playback.updated", {
        "state": pb.state,
        "current_session_track_id": str(pb.current_session_track_id) if pb.current_session_track_id else None,
        "position_ms": pb.position_ms,
    })
    return pb


@router.post("/sessions/{code}/playback/seek", response_model=PlaybackOut)
async def seek(
    code: str,
    body: SeekRequest,
    pair: Annotated[tuple[SessionMember, Session], Depends(require_host)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    _, session = pair
    pb = await _get_or_create_playback(db, session.id)
    pb.position_ms = body.position_ms
    pb.updated_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(pb)

    await manager.broadcast(session.id, "playback.updated", {"state": pb.state, "position_ms": pb.position_ms})
    return pb
