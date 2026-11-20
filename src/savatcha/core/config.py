from functools import lru_cache
from typing import Annotated

from pydantic import field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str
    bot_token_classic: str = ""
    bot_token_app: str = ""
    admin_ids: Annotated[list[int], NoDecode] = []
    require_receipt: bool = True
    upload_dir: str = "/data/uploads"
    max_upload_mb: int = 5
    webapp_url: str = ""
    initdata_max_age_seconds: int = 86400
    session_ttl_hours: int = 12
    stats_revenue_statuses: Annotated[list[str], NoDecode] = ["accepted", "delivering", "done"]
    shop_name: str = "Savatcha"
    shop_phone: str = "+998901234567"
    shop_hours: str = "09:00–21:00"
    app_env: str = "prod"  # "dev" bo'lsa /docs ochiq
    log_level: str = "INFO"

    @field_validator("admin_ids", "stats_revenue_statuses", mode="before")
    @classmethod
    def _split_csv(cls, v: object) -> object:
        if isinstance(v, str):
            return [p.strip() for p in v.split(",") if p.strip()]
        return v


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]
