import uuid
from datetime import datetime, timezone

import jwt
import structlog
from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect, WebSocketException, status

from app.database import AsyncSessionLocal
from app.models.session import Session, SessionMember
from app.services.broadcast import manager
from app.services.token import decode_token
from sqlalchemy import select

router = APIRouter(tags=["websocket"])
logger = structlog.get_logger()


async def _authenticate_ws(token: str, code: str) -> tuple[SessionMember, Session] | None:
    """Decode the JWT and verify member belongs to the requested session."""
    try:
        payload = decode_token(token)
    except jwt.InvalidTokenError:
        return None

    member_id = uuid.UUID(payload["sub"])
    async with AsyncSessionLocal() as db:
        member_result = await db.execute(select(SessionMember).where(SessionMember.id == member_id))
        member = member_result.scalar_one_or_none()
        if member is None or member.is_banned:
            return None

        session_result = await db.execute(select(Session).where(Session.code == code, Session.status == "ACTIVE"))
        session = session_result.scalar_one_or_none()
        if session is None or member.session_id != session.id:
            return None

        return member, session


@router.websocket("/ws/sessions/{code}")
async def websocket_endpoint(
    websocket: WebSocket,
    code: str,
    token: str = Query(...),
):
    auth = await _authenticate_ws(token, code)
    if auth is None:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    member, session = auth
    await manager.connect(session.id, websocket)
    logger.info("ws.auth_ok", member_id=str(member.id), session_id=str(session.id))

    try:
        while True:
            # Keep connection alive; client messages are ignored (server-push only)
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        manager.disconnect(session.id, websocket)
