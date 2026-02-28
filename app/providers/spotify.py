import httpx
import structlog

from app.providers.base import TrackMetadata

logger = structlog.get_logger()


async def resolve_spotify(provider_track_id: str, source_url: str | None) -> TrackMetadata:
    """
    Resolve Spotify track metadata via oEmbed (no OAuth required for basic info).
    Falls back to empty metadata on failure.
    """
    url = source_url or f"https://open.spotify.com/track/{provider_track_id}"
    oembed_url = f"https://open.spotify.com/oembed?url={url}"

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(oembed_url)
            resp.raise_for_status()
            data = resp.json()

        # oEmbed returns title like "Track Title by Artist"
        title_raw = data.get("title", "")
        artist = None
        title = title_raw
        if " by " in title_raw:
            parts = title_raw.rsplit(" by ", 1)
            title = parts[0].strip()
            artist = parts[1].strip()

        return TrackMetadata(
            title=title,
            artist=artist,
            artwork_url=data.get("thumbnail_url"),
        )
    except Exception as e:
        logger.warning("spotify.oembed_failed", error=str(e), track_id=provider_track_id)
        return TrackMetadata()
