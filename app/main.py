from contextlib import asynccontextmanager
import asyncio

import structlog
from arq import create_pool
from arq.connections import RedisSettings
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from redis.asyncio import Redis

from app.config import settings
from app.database import engine
from app.middleware import add_middleware
from app.routers import members, playback, sessions, tracks, votes, ws
from app.services.broadcast import CHANNEL_PREFIX, manager

logger = structlog.get_logger()


async def _pubsub_listener(redis: Redis) -> None:
    """Subscribe to all session:* channels and relay messages to in-process WS clients."""
    pubsub = redis.pubsub()
    await pubsub.psubscribe(f"{CHANNEL_PREFIX}*")
    try:
        async for message in pubsub.listen():
            if message["type"] != "pmessage":
                continue
            channel: str = message["channel"]
            session_id_str = channel.removeprefix(CHANNEL_PREFIX)
            await manager.broadcast_local(session_id_str, message["data"])
    except asyncio.CancelledError:
        pass
    finally:
        await pubsub.punsubscribe(f"{CHANNEL_PREFIX}*")
        await pubsub.aclose()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    app.state.redis = Redis.from_url(settings.REDIS_URL, decode_responses=True)
    app.state.arq = await create_pool(RedisSettings.from_dsn(settings.REDIS_URL))
    manager.set_redis(app.state.redis)
    pubsub_task = asyncio.create_task(_pubsub_listener(app.state.redis))
    logger.info("startup", redis_url=settings.REDIS_URL)
    yield
    # Shutdown
    pubsub_task.cancel()
    await asyncio.gather(pubsub_task, return_exceptions=True)
    await app.state.redis.aclose()
    await app.state.arq.aclose()
    await engine.dispose()
    logger.info("shutdown")


app = FastAPI(title="PassTheAux", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

add_middleware(app)

app.include_router(sessions.router, prefix="/v1")
app.include_router(tracks.router, prefix="/v1")
app.include_router(votes.router, prefix="/v1")
app.include_router(playback.router, prefix="/v1")
app.include_router(members.router, prefix="/v1")
app.include_router(ws.router, prefix="/v1")


@app.get("/health")
async def health():
    return {"status": "ok"}
