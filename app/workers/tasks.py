import json
import uuid

import structlog
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.database import AsyncSessionLocal
from app.models.track import SessionTrack, Track
from app.providers.apple import resolve_apple
from app.providers.spotify import resolve_spotify
from app.providers.youtube import resolve_youtube
from app.services.broadcast import CHANNEL_PREFIX

logger = structlog.get_logger()


async def resolve_track_metadata(ctx: dict, session_track_id: str) -> None:
    """
    ARQ background task: resolve track metadata from the provider,
    update the Track record, and publish track.updated to Redis pub/sub
    so the main app's listener relays it to connected WebSocket clients.

    ctx["redis"] is provided by ARQ and is an ArqRedis (asyncio-compatible).
    """
    redis = ctx["redis"]

    async with AsyncSessionLocal() as db:
        st_result = await db.execute(
            select(SessionTrack)
            .where(SessionTrack.id == uuid.UUID(session_track_id))
            .options(selectinload(SessionTrack.track))
        )
        session_track = st_result.scalar_one_or_none()
        if session_track is None:
            logger.warning("worker.session_track_not_found", session_track_id=session_track_id)
            return

        track = session_track.track
        if track.metadata_status == "RESOLVED":
            return  # already resolved by another session

        provider = track.provider
        provider_track_id = track.provider_track_id
        source_url = track.source_url

        logger.info("worker.resolving", provider=provider, track_id=str(track.id))

        if provider == "SPOTIFY":
            meta = await resolve_spotify(provider_track_id, source_url)
        elif provider == "YOUTUBE":
            meta = await resolve_youtube(provider_track_id, source_url)
        elif provider == "APPLE":
            meta = await resolve_apple(provider_track_id, source_url)
        else:
            logger.warning("worker.unknown_provider", provider=provider)
            track.metadata_status = "FAILED"
            await db.commit()
            return

        if meta.title:
            track.title = meta.title
            track.artist = meta.artist
            track.duration_ms = meta.duration_ms
            track.artwork_url = meta.artwork_url
            if meta.explicit is not None:
                track.explicit = meta.explicit
            track.metadata_status = "RESOLVED"
        else:
            track.metadata_status = "FAILED"

        await db.commit()
        await db.refresh(track)

        # Publish directly to Redis pub/sub — the main app's listener delivers to WS
        session_id = session_track.session_id
        message = json.dumps({
            "type": "track.updated",
            "data": {
                "session_track_id": session_track_id,
                "track": {
                    "id": str(track.id),
                    "title": track.title,
                    "artist": track.artist,
                    "artwork_url": track.artwork_url,
                    "duration_ms": track.duration_ms,
                    "metadata_status": track.metadata_status,
                },
            },
        })
        await redis.publish(f"{CHANNEL_PREFIX}{session_id}", message)
        logger.info("worker.resolved", track_id=str(track.id), status=track.metadata_status)
