from arq.connections import RedisSettings

from app.config import settings
from app.workers.tasks import resolve_track_metadata


class WorkerSettings:
    functions = [resolve_track_metadata]
    redis_settings = RedisSettings.from_dsn(settings.REDIS_URL)
    max_jobs = 10
    job_timeout = 30
