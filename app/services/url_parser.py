from urllib.parse import parse_qs, urlparse


def parse_track_url(url: str) -> tuple[str, str] | None:
    """
    Parse a music provider URL and return (provider, provider_track_id).
    Returns None if the URL is not recognized.
    """
    parsed = urlparse(url)
    hostname = parsed.hostname or ""

    # Spotify: https://open.spotify.com/track/{id}
    if "spotify.com" in hostname:
        parts = [p for p in parsed.path.split("/") if p]
        if len(parts) >= 2 and parts[0] == "track":
            return "SPOTIFY", parts[1].split("?")[0]

    # YouTube: https://www.youtube.com/watch?v={id} or https://youtu.be/{id}
    if "youtube.com" in hostname or "youtu.be" in hostname:
        if "youtu.be" in hostname:
            vid = parsed.path.lstrip("/").split("?")[0]
            if vid:
                return "YOUTUBE", vid
        qs = parse_qs(parsed.query)
        vid = qs.get("v", [None])[0]
        if vid:
            return "YOUTUBE", vid

    # Apple Music: https://music.apple.com/{country}/album/{name}/{album_id}?i={track_id}
    if "music.apple.com" in hostname:
        qs = parse_qs(parsed.query)
        track_id = qs.get("i", [None])[0]
        if track_id:
            return "APPLE", track_id

    return None
