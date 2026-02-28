from datetime import datetime, timedelta, timezone
from typing import Annotated

import structlog
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import require_host_or_mod
from app.models.session import Session, SessionMember
from app.schemas.member import MemberOut, MuteRequest
from app.services.broadcast import manager
from app.services.events import audit

router = APIRouter(tags=["members"])
logger = structlog.get_logger()


@router.post("/sessions/{code}/members/{member_id}/ban", response_model=MemberOut)
async def ban_member(
    code: str,
    member_id: str,
    pair: Annotated[tuple[SessionMember, Session], Depends(require_host_or_mod)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    _, session = pair

    result = await db.execute(
        select(SessionMember).where(SessionMember.id == member_id, SessionMember.session_id == session.id)
    )
    target = result.scalar_one_or_none()
    if target is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Member not found")
    if target.role == "HOST":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cannot ban the host")

    target.is_banned = True
    await audit(db, session.id, "member.banned", {"member_id": member_id, "display_name": target.display_name})
    await db.commit()
    await db.refresh(target)

    await manager.broadcast(session.id, "member.banned", {"member_id": member_id, "display_name": target.display_name})
    logger.info("member.banned", member_id=member_id, session_id=str(session.id))
    return target


@router.post("/sessions/{code}/members/{member_id}/mute", response_model=MemberOut)
async def mute_member(
    code: str,
    member_id: str,
    body: MuteRequest,
    pair: Annotated[tuple[SessionMember, Session], Depends(require_host_or_mod)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    _, session = pair

    result = await db.execute(
        select(SessionMember).where(SessionMember.id == member_id, SessionMember.session_id == session.id)
    )
    target = result.scalar_one_or_none()
    if target is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Member not found")
    if target.role == "HOST":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cannot mute the host")

    target.muted_until = datetime.now(timezone.utc) + timedelta(seconds=body.seconds)
    await db.commit()
    await db.refresh(target)

    logger.info("member.muted", member_id=member_id, seconds=body.seconds)
    return target
