from typing import Annotated

import structlog
from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.dependencies import get_arq, get_redis, require_host_or_mod, require_member_in_session
from app.models.session import Session, SessionMember
from app.models.track import SessionTrack, Track
from app.providers.spotify import fetch_spotify_playlist_tracks
from app.schemas.track import PlaylistImportRequest, PlaylistImportResult, SessionTrackOut, TrackAddRequest
from app.services.broadcast import manager
from app.services.events import audit
from app.services.queue import QueueEntry, rank_queue
from app.services.ratelimit import check_rate_limit
from app.services.url_parser import parse_playlist_url, parse_track_url

router = APIRouter(tags=["tracks"])
logger = structlog.get_logger()


async def build_queue_snapshot(db: AsyncSession, session_id) -> list[dict]:
    result = await db.execute(
        select(SessionTrack)
        .where(SessionTrack.session_id == session_id, SessionTrack.status == "QUEUED")
        .options(selectinload(SessionTrack.track))
    )
    rows = result.scalars().all()

    entries = [
        QueueEntry(
            session_track_id=r.id,
            track_id=r.track_id,
            added_by_member_id=r.added_by_member_id,
            added_at=r.added_at,
            score=r.score_cached,
            status=r.status,
        )
        for r in rows
    ]

    ranked = rank_queue(entries)
    rows_by_id = {r.id: r for r in rows}

    return [
        {
            "session_track_id": str(e.session_track_id),
            "score": e.score,
            "status": rows_by_id[e.session_track_id].status,
        }
        for e in ranked
    ]


@router.post(
    "/sessions/{code}/tracks",
    response_model=SessionTrackOut,
    status_code=status.HTTP_201_CREATED,
)
async def add_track(
    code: str,
    body: TrackAddRequest,
    pair: Annotated[tuple[SessionMember, Session], Depends(require_member_in_session)],
    db: Annotated[AsyncSession, Depends(get_db)],
    redis=Depends(get_redis),
    arq=Depends(get_arq),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
):
    member, session = pair
    sess_settings = session.settings or {}

    # Permission checks
    if not sess_settings.get("allow_guest_add", True) and member.role == "GUEST":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Guests cannot add tracks")

    # Rate limit
    allowed = await check_rate_limit(
        redis,
        key=f"rl:adds:{member.id}",
        limit=sess_settings.get("max_adds_per_guest_per_10min", 3),
        window_seconds=600,
    )
    if not allowed:
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="Add rate limit exceeded")

    # Resolve provider + id
    if body.url:
        parsed = parse_track_url(body.url)
        if not parsed:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Unrecognized provider URL")
        provider, provider_track_id = parsed
        source_url = body.url
    elif body.provider and body.provider_track_id:
        provider = body.provider.upper()
        provider_track_id = body.provider_track_id
        source_url = None
    else:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Provide either url or provider+provider_track_id",
        )

    # Upsert Track (global normalized table)
    existing_track_result = await db.execute(
        select(Track).where(Track.provider == provider, Track.provider_track_id == provider_track_id)
    )
    track = existing_track_result.scalar_one_or_none()
    if track is None:
        track = Track(provider=provider, provider_track_id=provider_track_id, source_url=source_url)
        db.add(track)
        await db.flush()

    # Dedupe check within session
    if sess_settings.get("dedupe_tracks", True):
        dup_result = await db.execute(
            select(SessionTrack).where(
                SessionTrack.session_id == session.id,
                SessionTrack.track_id == track.id,
                SessionTrack.status != "REMOVED",
            )
        )
        if dup_result.scalar_one_or_none() is not None:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Track already in queue")

    session_track = SessionTrack(
        session_id=session.id,
        track_id=track.id,
        added_by_member_id=member.id,
    )
    db.add(session_track)
    await audit(db, session.id, "track.added", {
        "session_track_id": str(session_track.id),
        "provider": provider,
        "provider_track_id": provider_track_id,
        "added_by": str(member.id),
    })
    await db.commit()
    await db.refresh(session_track)
    await db.refresh(track)

    # Enqueue metadata resolution job
    try:
        await arq.enqueue_job("resolve_track_metadata", str(session_track.id))
    except Exception as e:
        logger.warning("arq.enqueue_failed", error=str(e), session_track_id=str(session_track.id))

    logger.info("track.added", session_track_id=str(session_track.id), track_id=str(track.id))

    st_result = await db.execute(
        select(SessionTrack)
        .where(SessionTrack.id == session_track.id)
        .options(selectinload(SessionTrack.track), selectinload(SessionTrack.added_by))
    )
    st = st_result.scalar_one()

    await manager.broadcast(session.id, "track.added", {"session_track_id": str(st.id), "track_id": str(track.id)})
    queue_snapshot = await build_queue_snapshot(db, session.id)
    await manager.broadcast(session.id, "queue.updated", {"queue": queue_snapshot})

    return st


@router.get("/sessions/{code}/tracks", response_model=list[SessionTrackOut])
async def list_tracks(
    code: str,
    pair: Annotated[tuple[SessionMember, Session], Depends(require_member_in_session)],
    db: Annotated[AsyncSession, Depends(get_db)],
    track_status: str | None = None,
):
    _, session = pair
    query = (
        select(SessionTrack)
        .where(SessionTrack.session_id == session.id)
        .options(selectinload(SessionTrack.track), selectinload(SessionTrack.added_by))
    )
    if track_status:
        query = query.where(SessionTrack.status == track_status.upper())

    result = await db.execute(query)
    return result.scalars().all()


@router.delete("/sessions/{code}/tracks/{session_track_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_track(
    code: str,
    session_track_id: str,
    pair: Annotated[tuple[SessionMember, Session], Depends(require_host_or_mod)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    _, session = pair
    result = await db.execute(
        select(SessionTrack).where(SessionTrack.id == session_track_id, SessionTrack.session_id == session.id)
    )
    st = result.scalar_one_or_none()
    if st is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Track not found")

    st.status = "REMOVED"
    await audit(db, session.id, "track.removed", {"session_track_id": session_track_id})
    await db.commit()

    await manager.broadcast(session.id, "track.removed", {"session_track_id": session_track_id})
    queue_snapshot = await build_queue_snapshot(db, session.id)
    await manager.broadcast(session.id, "queue.updated", {"queue": queue_snapshot})


@router.post(
    "/sessions/{code}/import",
    response_model=PlaylistImportResult,
)
async def import_playlist(
    code: str,
    body: PlaylistImportRequest,
    pair: Annotated[tuple[SessionMember, Session], Depends(require_host_or_mod)],
    db: Annotated[AsyncSession, Depends(get_db)],
    redis=Depends(get_redis),
    arq=Depends(get_arq),
):
    from app.config import settings as app_settings

    member, session = pair
    sess_settings = session.settings or {}

    parsed = parse_playlist_url(body.url)
    if not parsed:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Unrecognized playlist URL")

    provider, playlist_id = parsed

    if provider == "SPOTIFY":
        if not app_settings.SPOTIFY_CLIENT_ID or not app_settings.SPOTIFY_CLIENT_SECRET:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Spotify credentials not configured on this server",
            )
        try:
            track_ids = await fetch_spotify_playlist_tracks(
                playlist_id,
                app_settings.SPOTIFY_CLIENT_ID,
                app_settings.SPOTIFY_CLIENT_SECRET,
            )
        except Exception as e:
            logger.warning("import.spotify_fetch_failed", error=str(e), playlist_id=playlist_id)
            raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Failed to fetch playlist from Spotify")
    else:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Only Spotify playlists are supported")

    added = skipped = errors = 0
    dedupe = sess_settings.get("dedupe_tracks", True)

    for spotify_track_id in track_ids:
        try:
            existing_track_result = await db.execute(
                select(Track).where(Track.provider == "SPOTIFY", Track.provider_track_id == spotify_track_id)
            )
            track = existing_track_result.scalar_one_or_none()
            if track is None:
                track = Track(
                    provider="SPOTIFY",
                    provider_track_id=spotify_track_id,
                    source_url=f"https://open.spotify.com/track/{spotify_track_id}",
                )
                db.add(track)
                await db.flush()

            if dedupe:
                dup_result = await db.execute(
                    select(SessionTrack).where(
                        SessionTrack.session_id == session.id,
                        SessionTrack.track_id == track.id,
                        SessionTrack.status != "REMOVED",
                    )
                )
                if dup_result.scalar_one_or_none() is not None:
                    skipped += 1
                    continue

            session_track = SessionTrack(
                session_id=session.id,
                track_id=track.id,
                added_by_member_id=member.id,
            )
            db.add(session_track)
            await db.flush()

            try:
                await arq.enqueue_job("resolve_track_metadata", str(session_track.id))
            except Exception as e:
                logger.warning("arq.enqueue_failed", error=str(e), session_track_id=str(session_track.id))

            await manager.broadcast(
                session.id, "track.added", {"session_track_id": str(session_track.id), "track_id": str(track.id)}
            )
            added += 1

        except Exception as e:
            logger.warning("import.track_failed", error=str(e), spotify_track_id=spotify_track_id)
            errors += 1

    await db.commit()

    queue_snapshot = await build_queue_snapshot(db, session.id)
    await manager.broadcast(session.id, "queue.updated", {"queue": queue_snapshot})

    logger.info("import.done", added=added, skipped=skipped, errors=errors, playlist_id=playlist_id)
    return PlaylistImportResult(added=added, skipped=skipped, errors=errors)
