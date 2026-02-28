import httpx
import structlog

from app.providers.base import TrackMetadata

logger = structlog.get_logger()


async def resolve_apple(provider_track_id: str, source_url: str | None) -> TrackMetadata:
    """
    Resolve Apple Music track metadata via oEmbed.
    Note: oEmbed returns limited info; upgrade to MusicKit API for full metadata.
    """
    if source_url is None:
        logger.warning("apple.no_source_url", track_id=provider_track_id)
        return TrackMetadata()

    oembed_url = f"https://music.apple.com/oembed?url={source_url}"

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(oembed_url)
            resp.raise_for_status()
            data = resp.json()

        title_raw = data.get("title", "")
        return TrackMetadata(
            title=title_raw,
            artwork_url=data.get("thumbnail_url"),
        )
    except Exception as e:
        logger.warning("apple.oembed_failed", error=str(e), track_id=provider_track_id)
        return TrackMetadata()
