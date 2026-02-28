from typing import Annotated

import structlog
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import require_host, require_member_in_session
from app.models.playback import PlaybackState
from app.models.session import Session, SessionMember
from app.schemas.session import (
    SessionCreate,
    SessionCreateResponse,
    SessionJoin,
    SessionJoinResponse,
    SessionOut,
    SettingsUpdate,
)
from app.services.broadcast import manager
from app.services.events import audit
from app.services.session_code import generate_session_code
from app.services.token import create_token

router = APIRouter(tags=["sessions"])
logger = structlog.get_logger()


@router.post("/sessions", response_model=SessionCreateResponse, status_code=status.HTTP_201_CREATED)
async def create_session(
    body: SessionCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    # Ensure unique code
    for _ in range(10):
        code = generate_session_code()
        existing = await db.execute(select(Session).where(Session.code == code))
        if existing.scalar_one_or_none() is None:
            break
    else:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Could not generate unique code")

    session = Session(code=code, title=body.title)
    db.add(session)
    await db.flush()  # get session.id

    host = SessionMember(session_id=session.id, display_name="Host", role="HOST")
    db.add(host)
    await db.flush()

    # Initialize playback state
    playback = PlaybackState(session_id=session.id)
    db.add(playback)
    await audit(db, session.id, "session.created", {"title": body.title, "code": code})

    await db.commit()
    await db.refresh(session)
    await db.refresh(host)

    token = create_token(host.id, session.id, "HOST")
    logger.info("session.created", session_id=str(session.id), code=code)

    return SessionCreateResponse(session_id=session.id, code=code, host_token=token)


@router.post("/sessions/{code}/join", response_model=SessionJoinResponse, status_code=status.HTTP_201_CREATED)
async def join_session(
    code: str,
    body: SessionJoin,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    result = await db.execute(select(Session).where(Session.code == code, Session.status == "ACTIVE"))
    session = result.scalar_one_or_none()
    if session is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found or ended")

    # Check display_name uniqueness — append suffix if taken
    display_name = body.display_name
    existing = await db.execute(
        select(SessionMember).where(SessionMember.session_id == session.id, SessionMember.display_name == display_name)
    )
    if existing.scalar_one_or_none() is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Display name already taken in this session")

    member = SessionMember(session_id=session.id, display_name=display_name, role="GUEST")
    db.add(member)
    await audit(db, session.id, "member.joined", {"member_id": str(member.id), "display_name": display_name})
    await db.commit()
    await db.refresh(member)

    token = create_token(member.id, session.id, "GUEST")
    logger.info("member.joined", session_id=str(session.id), member_id=str(member.id))

    await manager.broadcast(session.id, "member.joined", {"member_id": str(member.id), "display_name": member.display_name})

    return SessionJoinResponse(member_id=member.id, member_token=token, role="GUEST")


@router.get("/sessions/{code}", response_model=SessionOut)
async def get_session(
    pair: Annotated[tuple, Depends(require_member_in_session)],
):
    _, session = pair
    return session


@router.patch("/sessions/{code}/settings", response_model=SessionOut)
async def update_settings(
    body: SettingsUpdate,
    pair: Annotated[tuple, Depends(require_host)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    _, session = pair
    session.settings = body.settings
    db.add(session)
    await db.commit()
    await db.refresh(session)

    await manager.broadcast(session.id, "session.updated", {"settings": session.settings})
    return session
