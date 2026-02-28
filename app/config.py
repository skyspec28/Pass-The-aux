from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    DATABASE_URL: str = "postgresql+asyncpg://passtheaux:passtheaux@localhost:5432/passtheaux"
    REDIS_URL: str = "redis://localhost:6379"
    SECRET_KEY: str = "dev-secret-change-in-prod"
    TOKEN_EXPIRE_SECONDS: int = 86400

    # Provider keys (optional)
    SPOTIFY_CLIENT_ID: str = ""
    SPOTIFY_CLIENT_SECRET: str = ""
    YOUTUBE_API_KEY: str = ""


settings = Settings()
