"""Application settings loaded from environment variables.

All values are overridable through ``OSCAR_``-prefixed environment variables so
that local development, tests, and Docker Compose can point at different
databases without code changes. No secret has a production-looking default.
"""

from functools import lru_cache
from typing import Self

from pydantic import Field, model_validator
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
    database_pool_size: int = Field(default=3, ge=1, le=5)
    database_max_overflow: int = Field(default=1, ge=0, le=3)

    # Auth / RBAC. The default secret is intentionally marked unsafe; deployments
    # must override OSCAR_JWT_SECRET.
    jwt_secret: str = "dev-only-unsafe-secret-change-me"
    jwt_algorithm: str = "HS256"
    jwt_expires_minutes: int = 60 * 8
    enable_demo_seed: bool = False

    # Observability
    log_level: str = "INFO"
    log_json: bool = True

    # Browser origins allowed to call the API (workbench dev/preview servers).
    cors_origins: list[str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:4173",
        "http://127.0.0.1:4173",
    ]

    # Decision runtime
    decision_default_product_segment: str = "DEFAULT"

    # Manual-review SLA target hours per case priority (Phase 2).
    sla_hours_high: int = 4
    sla_hours_medium: int = 24
    sla_hours_low: int = 72

    # Full maker-checker: require an attached simulation of the exact strategy
    # version before it can be activated (docs/14 §6, Phase 2).
    require_strategy_simulation_before_activation: bool = True

    @model_validator(mode="after")
    def reject_unsafe_server_settings(self) -> Self:
        """Do not allow development credentials or demo seeding in hosted environments."""
        local_environments = {"development", "test", "testing", "compose", "local"}
        if self.environment.lower() not in local_environments:
            if (
                self.jwt_secret
                in {
                    "dev-only-unsafe-secret-change-me",
                    "compose-dev-secret-not-for-production",
                    "ci-test-only-secret-not-for-any-deployment",
                    "replace-with-a-strong-random-secret",
                }
                or self.jwt_secret.startswith("REPLACE_")
                or len(self.jwt_secret) < 32
            ):
                raise ValueError(
                    "OSCAR_JWT_SECRET must be a strong secret in non-local environments"
                )
            if "oscar_dev_password" in self.database_url:
                raise ValueError("Development database credentials cannot be used for deployment")
            if self.enable_demo_seed:
                raise ValueError("OSCAR_ENABLE_DEMO_SEED must be false outside local development")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
