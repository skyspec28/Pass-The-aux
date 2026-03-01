import base64

import httpx
import structlog

from app.providers.base import TrackMetadata

logger = structlog.get_logger()

_token_cache: dict = {}  # {"token": str, "expires_at": float}


async def _get_client_token(client_id: str, client_secret: str) -> str:
    """Obtain a Spotify Client Credentials access token, cached until expiry."""
    import time

    cached = _token_cache.get("token")
    if cached and _token_cache.get("expires_at", 0) > time.time() + 30:
        return cached

    credentials = base64.b64encode(f"{client_id}:{client_secret}".encode()).decode()
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.post(
            "https://accounts.spotify.com/api/token",
            headers={"Authorization": f"Basic {credentials}"},
            data={"grant_type": "client_credentials"},
        )
        resp.raise_for_status()
        data = resp.json()

    _token_cache["token"] = data["access_token"]
    _token_cache["expires_at"] = time.time() + data["expires_in"]
    return data["access_token"]


async def fetch_spotify_playlist_tracks(playlist_id: str, client_id: str, client_secret: str) -> list[str]:
    """
    Fetch all Spotify track IDs from a playlist using the Web API.
    Returns a list of provider_track_ids (Spotify track IDs).
    Handles pagination automatically.
    """
    token = await _get_client_token(client_id, client_secret)
    track_ids: list[str] = []
    url: str | None = (
        f"https://api.spotify.com/v1/playlists/{playlist_id}/tracks"
        "?fields=next,items(track(id,is_local))&limit=100"
    )

    async with httpx.AsyncClient(timeout=15.0) as client:
        while url:
            resp = await client.get(url, headers={"Authorization": f"Bearer {token}"})
            resp.raise_for_status()
            data = resp.json()
            for item in data.get("items", []):
                track = item.get("track")
                if track and not track.get("is_local") and track.get("id"):
                    track_ids.append(track["id"])
            url = data.get("next")

    return track_ids


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
