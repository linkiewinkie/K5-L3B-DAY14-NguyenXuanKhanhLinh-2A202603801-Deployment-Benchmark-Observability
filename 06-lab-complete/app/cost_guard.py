"""Reserve budget atomically and settle usage after the mock LLM call."""
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException

from utils.mock_llm import MOCK_RESPONSES

from .config import settings
from .redis_client import r

NANODOLLARS_PER_USD = 1_000_000_000
# Pricing of $0.00015 input and $0.0006 output per 1,000 tokens.
INPUT_TOKEN_PRICE = 150
OUTPUT_TOKEN_PRICE = 600

reserve = r.register_script("""
local used = tonumber(redis.call('GET', KEYS[1]) or '0')
local cost = tonumber(ARGV[1])
if used + cost > tonumber(ARGV[2]) then
    return 0
end
redis.call('SET', KEYS[1], used + cost, 'EXAT', ARGV[3])
return 1
""")

settle = r.register_script("""
if redis.call('EXISTS', KEYS[1]) == 1 then
    redis.call('DECRBY', KEYS[1], ARGV[1])
end
""")


def estimate_tokens(text: str) -> int:
    return max(1, (len(text) + 3) // 4)


MAX_OUTPUT_TOKENS = max(
    estimate_tokens(answer) for answers in MOCK_RESPONSES.values() for answer in answers
)


def check_budget(input_tokens: int) -> tuple[str, int]:
    now = datetime.now(timezone.utc)
    if settings.daily_budget_usd is not None:
        period = now.strftime("%Y-%m-%d")
        expiration = (now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
        budget = settings.daily_budget_usd
    else:
        period = now.strftime("%Y-%m")
        first = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        expiration = (first + timedelta(days=32)).replace(day=1)
        budget = settings.monthly_budget_usd

    key = f"day14:{settings.environment}:budget:{period}"
    reserved_cost = input_tokens * INPUT_TOKEN_PRICE + MAX_OUTPUT_TOKENS * OUTPUT_TOKEN_PRICE
    allowed = reserve(
        keys=[key],
        args=[reserved_cost, int(budget * NANODOLLARS_PER_USD), int(expiration.timestamp())],
    )
    if not allowed:
        raise HTTPException(status_code=402, detail="LLM budget exceeded")
    return key, reserved_cost


def record_cost(reservation: tuple[str, int], input_tokens: int, output_tokens: int) -> float:
    key, reserved_cost = reservation
    actual_cost = input_tokens * INPUT_TOKEN_PRICE + output_tokens * OUTPUT_TOKEN_PRICE
    settle(keys=[key], args=[reserved_cost - actual_cost])
    return actual_cost / NANODOLLARS_PER_USD
