from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_prefix="", extra="ignore")

    orbitrisk_env: str = Field(default="local", alias="ORBITRISK_ENV")
    sentinelhub_client_id: str | None = Field(default=None, alias="SENTINELHUB_CLIENT_ID")
    sentinelhub_client_secret: str | None = Field(default=None, alias="SENTINELHUB_CLIENT_SECRET")
    sentinelhub_base_url: str = Field(
        default="https://services.sentinel-hub.com",
        alias="SENTINELHUB_BASE_URL",
    )
    default_resolution_m: int = Field(default=10, alias="ORBITRISK_DEFAULT_RESOLUTION_M")
    min_valid_pixels: int = Field(default=20, alias="ORBITRISK_MIN_VALID_PIXELS")

    @property
    def sentinelhub_enabled(self) -> bool:
        return bool(self.sentinelhub_client_id and self.sentinelhub_client_secret)


@lru_cache
def get_settings() -> Settings:
    return Settings()
