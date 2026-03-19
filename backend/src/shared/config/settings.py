from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = Field(default="Trading Platform", alias="APP_NAME")
    environment: str = Field(default="local", alias="ENVIRONMENT")
    debug: bool = Field(default=True, alias="DEBUG")
    api_prefix: str = "/api/v1"
    cors_origins: list[str] = Field(
        default=["http://localhost:3000", "http://127.0.0.1:3000"],
        alias="CORS_ORIGINS",
    )

    database_url: str = Field(default="postgresql://user:password@localhost:5432/trading_platform", alias="DATABASE_URL")
    redis_url: str = Field(default="redis://localhost:6379/0", alias="REDIS_URL")

    secret_key: str = Field(default="change-me", alias="SECRET_KEY")
    algorithm: str = Field(default="HS256", alias="ALGORITHM")
    access_token_expire_minutes: int = Field(default=30, alias="ACCESS_TOKEN_EXPIRE_MINUTES")

    ig_api_key: str = Field(default="", alias="IG_API_KEY")
    ig_api_url: str = Field(default="https://demo-api.ig.com/gateway/deal", alias="IG_API_URL")
    ig_timeout_seconds: float = Field(default=15.0, alias="IG_TIMEOUT_SECONDS")
    execution_mode: str = Field(default="paper", alias="EXECUTION_MODE")
    default_watchlist_epics: list[str] = Field(
        default=[
            "CS.D.EURUSD.CFD.IP",
            "CS.D.GBPUSD.CFD.IP",
            "CS.D.USDJPY.CFD.IP",
            "CS.D.AUDUSD.CFD.IP",
            "CS.D.NZDUSD.CFD.IP",
            "CS.D.USDCAD.CFD.IP",
            "CS.D.EURJPY.CFD.IP",
            "CS.D.GBPJPY.CFD.IP",
            "CS.D.EURGBP.CFD.IP",
            "CS.D.USDCHF.CFD.IP",
        ],
        alias="DEFAULT_WATCHLIST_EPICS",
    )

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
