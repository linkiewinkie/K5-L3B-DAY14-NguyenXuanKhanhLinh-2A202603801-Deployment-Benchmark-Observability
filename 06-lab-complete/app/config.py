"""Environment configuration for the production agent."""
import os
from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class Settings:
    port: int
    environment: str
    agent_api_key: str
    redis_url: str
    rate_limit_per_minute: int
    daily_budget_usd: Decimal | None
    monthly_budget_usd: Decimal
    log_level: str

    @classmethod
    def from_env(cls) -> "Settings":
        daily_budget = os.getenv("DAILY_BUDGET_USD")
        return cls(
            port=int(os.getenv("PORT", "8000")),
            environment=os.getenv("ENVIRONMENT", "development"),
            agent_api_key=os.getenv("AGENT_API_KEY", ""),
            redis_url=os.getenv("REDIS_URL", "redis://127.0.0.1:6379/0"),
            rate_limit_per_minute=int(os.getenv("RATE_LIMIT_PER_MINUTE", "10")),
            daily_budget_usd=Decimal(daily_budget) if daily_budget else None,
            monthly_budget_usd=Decimal(os.getenv("MONTHLY_BUDGET_USD", "10")),
            log_level=os.getenv("LOG_LEVEL", "INFO").upper(),
        )


settings = Settings.from_env()
