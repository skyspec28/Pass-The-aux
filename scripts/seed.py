"""
Seed script — populate the database with a demo session for manual testing.

Run inside the app container:
  docker compose exec -e PYTHONPATH=/code app python scripts/seed.py

Re-running is safe — it clears the previous PARTY1 session first.
Prints the session code and JWT tokens for all members so you can immediately
hit the API or open a WebSocket without going through the auth flow.
"""
import asyncio
import uuid

from sqlalchemy import select, delete

from app.database import AsyncSessionLocal
from app.models.session import Session, SessionMember
from app.models.track import SessionTrack, Track
from app.models.vote import Vote
from app.models.playback import PlaybackState
from app.services.token import create_token

SESSION_CODE = "PARTY1"

TRACKS = [
    # (provider, provider_track_id, title, artist, duration_ms, artwork_url, source_url)
    (
        "SPOTIFY",
        "4iV5W9uYEdYUVa79Axb7Rh",
        "Never Gonna Give You Up",
        "Rick Astley",
        213573,
        "https://i.scdn.co/image/ab67616d0000b273696b20fffff1a96c0f5e9f2f",
        "https://open.spotify.com/track/4iV5W9uYEdYUVa79Axb7Rh",
    ),
    (
        "YOUTUBE",
        "dQw4w9WgXcQ",
        "Never Gonna Give You Up",
        "RickAstleyVEVO",
        212000,
        "https://i.ytimg.com/vi/dQw4w9WgXcQ/hqdefault.jpg",
        "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
    ),
    (
        "SPOTIFY",
        "3n3Ppam7vgaVa1iaRUIOKE",
        "Mr. Brightside",
        "The Killers",
        222973,
        "https://i.scdn.co/image/ab67616d0000b273d5a01c3c9eda5c93c8e5e3e3",
        "https://open.spotify.com/track/3n3Ppam7vgaVa1iaRUIOKE",
    ),
    (
        "YOUTUBE",
        "gGdGFtwCNBE",
        "Bohemian Rhapsody",
        "Queen Official",
        354000,
        "https://i.ytimg.com/vi/gGdGFtwCNBE/hqdefault.jpg",
        "https://www.youtube.com/watch?v=gGdGFtwCNBE",
    ),
    (
        "SPOTIFY",
        "7qiZfU4dY1lWllzX7mPBI3",
        "Shape of You",
        "Ed Sheeran",
        233713,
        "https://i.scdn.co/image/ab67616d0000b273ba5db46f4b838ef6027e6f96",
        "https://open.spotify.com/track/7qiZfU4dY1lWllzX7mPBI3",
    ),
]

MEMBERS = [
    ("Alice", "HOST"),
    ("Bob", "GUEST"),
    ("Carol", "GUEST"),
    ("Dave", "GUEST"),
]

# Votes: (adder_name, voter_name, value)
VOTES = [
    ("Alice", "Bob", 1),
    ("Alice", "Carol", 1),
    ("Alice", "Dave", 1),
    ("Bob", "Alice", 1),
    ("Bob", "Carol", -1),
    ("Carol", "Alice", 1),
    ("Carol", "Dave", -1),
    ("Dave", "Alice", 1),
]


async def clear_existing(db) -> None:
    result = await db.execute(select(Session).where(Session.code == SESSION_CODE))
    existing = result.scalar_one_or_none()
    if existing:
        await db.delete(existing)
        await db.flush()
        print(f"Cleared existing session {SESSION_CODE!r}")


async def seed() -> None:
    async with AsyncSessionLocal() as db:
        await clear_existing(db)

        # 1. Session
        session = Session(
            code=SESSION_CODE,
            title="PassTheAux Demo Party 🎵",
            status="ACTIVE",
            settings={
                "allow_guest_add": True,
                "allow_downvotes": True,
                "dedupe_tracks": True,
                "max_adds_per_guest_per_10min": 10,
                "max_votes_per_guest_per_min": 20,
                "fairness_enabled": True,
                "cooldown_songs": 1,
            },
        )
        db.add(session)
        await db.flush()

        # 2. Members
        member_map: dict[str, SessionMember] = {}
        for display_name, role in MEMBERS:
            m = SessionMember(
                session_id=session.id,
                display_name=display_name,
                role=role,
            )
            db.add(m)
            member_map[display_name] = m
        await db.flush()

        # 3. PlaybackState
        db.add(PlaybackState(session_id=session.id))
        await db.flush()

        # 4. Tracks + SessionTracks
        # Each track is added by MEMBERS[i % len(MEMBERS)] to spread ownership
        session_tracks: list[SessionTrack] = []
        adder_names = [name for name, _ in MEMBERS]

        for i, (provider, provider_track_id, title, artist, duration_ms, artwork_url, source_url) in enumerate(TRACKS):
            # Upsert global track
            existing = await db.execute(
                select(Track).where(
                    Track.provider == provider,
                    Track.provider_track_id == provider_track_id,
                )
            )
            track = existing.scalar_one_or_none()
            if track is None:
                track = Track(
                    provider=provider,
                    provider_track_id=provider_track_id,
                    title=title,
                    artist=artist,
                    duration_ms=duration_ms,
                    artwork_url=artwork_url,
                    source_url=source_url,
                    metadata_status="RESOLVED",
                )
                db.add(track)
                await db.flush()

            adder = member_map[adder_names[i % len(adder_names)]]
            st = SessionTrack(
                session_id=session.id,
                track_id=track.id,
                added_by_member_id=adder.id,
            )
            db.add(st)
            session_tracks.append((st, track, adder))
        await db.flush()

        # 5. Votes
        # Build a map: adder display_name -> list of SessionTrack ids they added
        adder_to_sts: dict[str, list] = {}
        for st, track, adder in session_tracks:
            adder_to_sts.setdefault(adder.display_name, []).append(st)

        # Cast votes
        votes_cast = 0
        for adder_name, voter_name, value in VOTES:
            sts = adder_to_sts.get(adder_name, [])
            voter = member_map[voter_name]
            for st, _, _ in [(s, t, a) for s, t, a in session_tracks if a.display_name == adder_name]:
                existing_vote = await db.execute(
                    select(Vote).where(
                        Vote.session_track_id == st.id,
                        Vote.member_id == voter.id,
                    )
                )
                if existing_vote.scalar_one_or_none() is None:
                    db.add(Vote(session_track_id=st.id, member_id=voter.id, value=value))
                    votes_cast += 1

        await db.flush()

        # 6. Recompute score_cached for each SessionTrack
        from sqlalchemy import func
        for st, _, _ in session_tracks:
            result = await db.execute(
                select(func.coalesce(func.sum(Vote.value), 0)).where(Vote.session_track_id == st.id)
            )
            st.score_cached = result.scalar_one()

        await db.commit()

        # 7. Print summary
        print()
        print("=" * 60)
        print(f"  Session code : {SESSION_CODE}")
        print(f"  Session ID   : {session.id}")
        print("=" * 60)
        print()
        print("MEMBER TOKENS (use as: Authorization: Bearer <token>)")
        print("-" * 60)
        for name, role in MEMBERS:
            m = member_map[name]
            token = create_token(m.id, session.id, role)
            print(f"  [{role:5}] {name:8}  {token}")
        print()
        print("TRACKS IN QUEUE")
        print("-" * 60)
        for st, track, adder in session_tracks:
            print(
                f"  {track.artist:20} — {track.title:30}"
                f"  score={st.score_cached:+d}  added_by={adder.display_name}"
            )
        print()
        print(f"  {votes_cast} votes cast across {len(session_tracks)} tracks")
        print()
        print("QUICK START")
        print("-" * 60)
        print(f"  GET  http://localhost:8080/v1/sessions/{SESSION_CODE}")
        print(f"  GET  http://localhost:8080/v1/sessions/{SESSION_CODE}/tracks")
        print(f"  WS   ws://localhost:8080/v1/ws/sessions/{SESSION_CODE}?token=<host_token>")
        print(f"  Docs http://localhost:8080/docs")
        print("=" * 60)
        print()


if __name__ == "__main__":
    asyncio.run(seed())
