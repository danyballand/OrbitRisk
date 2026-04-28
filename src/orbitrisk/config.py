from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_prefix="", extra="ignore")

    orbitrisk_env: str = Field(default="local", alias="ORBITRISK_ENV")
    data_provider: str = Field(default="planetary-computer", alias="ORBITRISK_DATA_PROVIDER")
    sentinelhub_client_id: str | None = Field(default=None, alias="SENTINELHUB_CLIENT_ID")
    sentinelhub_client_secret: str | None = Field(default=None, alias="SENTINELHUB_CLIENT_SECRET")
    sentinelhub_base_url: str = Field(
        default="https://services.sentinel-hub.com",
        alias="SENTINELHUB_BASE_URL",
    )
    planetary_computer_stac_url: str = Field(
        default="https://planetarycomputer.microsoft.com/api/stac/v1",
        alias="PLANETARY_COMPUTER_STAC_URL",
    )
    planetary_computer_collection: str = Field(
        default="sentinel-2-l2a",
        alias="PLANETARY_COMPUTER_COLLECTION",
    )
    default_resolution_m: int = Field(default=10, alias="ORBITRISK_DEFAULT_RESOLUTION_M")
    min_valid_pixels: int = Field(default=20, alias="ORBITRISK_MIN_VALID_PIXELS")
    cache_dir: Path = Field(default=Path("data/cache"), alias="ORBITRISK_CACHE_DIR")
    api_keys: str = Field(default="dev-orbitrisk-key", alias="ORBITRISK_API_KEYS")
    rate_limit_per_minute: int = Field(default=60, alias="ORBITRISK_RATE_LIMIT_PER_MINUTE")

    @property
    def sentinelhub_enabled(self) -> bool:
        return bool(self.sentinelhub_client_id and self.sentinelhub_client_secret)

    @property
    def api_key_set(self) -> set[str]:
        return {key.strip() for key in self.api_keys.split(",") if key.strip()}


@lru_cache
def get_settings() -> Settings:
    return Settings()
