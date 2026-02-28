import uuid
from datetime import datetime, timedelta, timezone

import jwt

from app.config import settings


def create_token(member_id: uuid.UUID, session_id: uuid.UUID, role: str) -> str:
    payload = {
        "sub": str(member_id),
        "session_id": str(session_id),
        "role": role,
        "exp": datetime.now(timezone.utc) + timedelta(seconds=settings.TOKEN_EXPIRE_SECONDS),
        "iat": datetime.now(timezone.utc),
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm="HS256")


def decode_token(token: str) -> dict:
    """Raises jwt.InvalidTokenError on bad/expired tokens."""
    return jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
