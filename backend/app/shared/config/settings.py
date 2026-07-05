"""Application settings loaded from environment variables.

All values are overridable through ``OSCAR_``-prefixed environment variables so
that local development, tests, and Docker Compose can point at different
databases without code changes. No secret has a production-looking default.
"""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="OSCAR_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "oscar-decision-engine"
    environment: str = "development"
    debug: bool = False

    database_url: str = "postgresql+asyncpg://oscar:oscar_dev_password@localhost:5455/oscar"
    database_echo: bool = False

    # Auth / RBAC. The default secret is intentionally marked unsafe; deployments
    # must override OSCAR_JWT_SECRET.
    jwt_secret: str = "dev-only-unsafe-secret-change-me"
    jwt_algorithm: str = "HS256"
    jwt_expires_minutes: int = 60 * 8

    # Observability
    log_level: str = "INFO"
    log_json: bool = True

    # Browser origins allowed to call the API (workbench dev/preview servers).
    cors_origins: list[str] = ["http://localhost:5173", "http://localhost:4173"]

    # Decision runtime
    decision_default_product_segment: str = "DEFAULT"

    # Manual-review SLA target hours per case priority (Phase 2).
    sla_hours_high: int = 4
    sla_hours_medium: int = 24
    sla_hours_low: int = 72


@lru_cache
def get_settings() -> Settings:
    return Settings()
