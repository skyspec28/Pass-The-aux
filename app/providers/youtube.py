import httpx
import structlog

from app.providers.base import TrackMetadata

logger = structlog.get_logger()


async def resolve_youtube(provider_track_id: str, source_url: str | None) -> TrackMetadata:
    """Resolve YouTube video metadata via oEmbed."""
    url = source_url or f"https://www.youtube.com/watch?v={provider_track_id}"
    oembed_url = f"https://www.youtube.com/oembed?url={url}&format=json"

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(oembed_url)
            resp.raise_for_status()
            data = resp.json()

        return TrackMetadata(
            title=data.get("title"),
            artist=data.get("author_name"),
            artwork_url=data.get("thumbnail_url"),
        )
    except Exception as e:
        logger.warning("youtube.oembed_failed", error=str(e), track_id=provider_track_id)
        return TrackMetadata()
