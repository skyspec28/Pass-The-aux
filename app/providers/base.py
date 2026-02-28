from dataclasses import dataclass


@dataclass
class TrackMetadata:
    title: str | None = None
    artist: str | None = None
    duration_ms: int | None = None
    artwork_url: str | None = None
    explicit: bool | None = None
