import uuid
from datetime import datetime, timezone
from typing import Annotated

import jwt
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.session import Session, SessionMember
from app.services.token import decode_token

bearer_scheme = HTTPBearer()


async def get_redis(request: Request):
    return request.app.state.redis


async def get_arq(request: Request):
    return request.app.state.arq


async def require_member(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(bearer_scheme)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> SessionMember:
    try:
        payload = decode_token(credentials.credentials)
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token")

    member_id = uuid.UUID(payload["sub"])
    result = await db.execute(select(SessionMember).where(SessionMember.id == member_id))
    member = result.scalar_one_or_none()

    if member is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Member not found")
    if member.is_banned:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You are banned from this session")
    if member.muted_until and member.muted_until > datetime.now(timezone.utc):
        pass  # muted members can still read; blocking happens at write endpoints

    return member


async def require_member_in_session(
    code: str,
    member: Annotated[SessionMember, Depends(require_member)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> tuple[SessionMember, Session]:
    result = await db.execute(select(Session).where(Session.code == code, Session.status == "ACTIVE"))
    session = result.scalar_one_or_none()
    if session is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found or ended")
    if member.session_id != session.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Token does not belong to this session")
    return member, session


async def require_host(
    pair: Annotated[tuple[SessionMember, Session], Depends(require_member_in_session)],
) -> tuple[SessionMember, Session]:
    member, session = pair
    if member.role != "HOST":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Host access required")
    return pair


async def require_host_or_mod(
    pair: Annotated[tuple[SessionMember, Session], Depends(require_member_in_session)],
) -> tuple[SessionMember, Session]:
    member, session = pair
    if member.role not in ("HOST", "MOD"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Moderator access required")
    return pair
