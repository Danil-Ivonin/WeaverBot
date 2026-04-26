from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    bot_token: str
    soundweaver_base_url: str
    database_url: str
    soundweaver_poll_interval_sec: float = Field(default=2.0, gt=0)
    soundweaver_poll_timeout_sec: float = Field(default=120.0, gt=0)
    log_level: str = "INFO"
