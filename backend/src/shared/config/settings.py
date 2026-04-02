from functools import lru_cache
from typing import Literal

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


IgEnvironment = Literal["demo", "live"]


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
    database_echo: bool = Field(default=False, alias="DATABASE_ECHO")
    database_pool_size: int = Field(default=5, alias="DATABASE_POOL_SIZE")
    database_max_overflow: int = Field(default=10, alias="DATABASE_MAX_OVERFLOW")
    database_pool_timeout_seconds: int = Field(default=30, alias="DATABASE_POOL_TIMEOUT_SECONDS")
    database_pool_recycle_seconds: int = Field(default=1800, alias="DATABASE_POOL_RECYCLE_SECONDS")
    database_auto_create_schema: bool = Field(default=False, alias="DATABASE_AUTO_CREATE_SCHEMA")
    redis_url: str = Field(default="redis://localhost:6379/0", alias="REDIS_URL")

    secret_key: str = Field(default="change-me", alias="SECRET_KEY")
    algorithm: str = Field(default="HS256", alias="ALGORITHM")
    access_token_expire_minutes: int = Field(default=30, alias="ACCESS_TOKEN_EXPIRE_MINUTES")

    ig_api_key: str = Field(default="", alias="IG_API_KEY")
    ig_api_url: str = Field(default="https://demo-api.ig.com/gateway/deal", alias="IG_API_URL")
    ig_environment: IgEnvironment = Field(default="demo", alias="IG_ENVIRONMENT")
    allow_live_trading: bool = Field(default=False, alias="ALLOW_LIVE_TRADING")
    ig_lightstreamer_url: str = Field(default="https://demo-apd.marketdatasystems.com", alias="IG_LIGHTSTREAMER_URL")
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

    @property
    def live_trading_enabled(self) -> bool:
        return self.ig_environment == "live" and self.allow_live_trading

    @property
    def broker_environment_label(self) -> str:
        return "IG Markets (LIVE)" if self.ig_environment == "live" else "IG Markets (DEMO)"

    @model_validator(mode="after")
    def validate_ig_environment(self) -> "Settings":
        api_url = self.ig_api_url.lower()
        stream_url = self.ig_lightstreamer_url.lower()

        if self.ig_environment == "demo":
            if "api.ig.com" in api_url and "demo-api.ig.com" not in api_url:
                raise ValueError("IG demo environment must use a demo API URL")
            if "apd.marketdatasystems.com" in stream_url and "demo-apd.marketdatasystems.com" not in stream_url:
                raise ValueError("IG demo environment must use a demo Lightstreamer URL")

        if self.ig_environment == "live":
            if "demo-api.ig.com" in api_url:
                raise ValueError("IG live environment cannot use the demo API URL")
            if "demo-apd.marketdatasystems.com" in stream_url:
                raise ValueError("IG live environment cannot use the demo Lightstreamer URL")

        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
