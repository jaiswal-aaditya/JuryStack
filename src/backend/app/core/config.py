from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Environment-backed process configuration."""

    model_config = SettingsConfigDict(
        env_prefix="JURYSTACK_",
        env_file=".env",
        extra="ignore",
    )

    app_name: str = "JuryStack API"
    database_url: str = (
        "postgresql+asyncpg://jurystack:jurystack@localhost:5432/jurystack"
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
