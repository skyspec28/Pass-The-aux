import time

from redis.asyncio import Redis


async def check_rate_limit(
    redis: Redis,
    key: str,
    limit: int,
    window_seconds: int,
) -> bool:
    """
    Sliding-window rate limiter using a Redis sorted set.
    Returns True if the action is allowed, False if rate-limited.
    """
    now = time.time()
    window_start = now - window_seconds

    pipe = redis.pipeline()
    pipe.zremrangebyscore(key, "-inf", window_start)
    pipe.zadd(key, {str(now): now})
    pipe.zcard(key)
    pipe.expire(key, window_seconds + 1)
    results = await pipe.execute()

    count = results[2]
    return count <= limit
