from __future__ import annotations

from datetime import datetime
from typing import Protocol


class PricingProvider(Protocol):
    def calculate(
        self, base_price: float, start: datetime, end: datetime, config: dict | None
    ) -> float: ...


def get_pricing_provider(model: str) -> PricingProvider:
    from app.domains.resources.pricing.providers import (
        FixedPerDayProvider,
        FixedPerSlotProvider,
        HourlyPricingProvider,
        TieredProvider,
    )

    providers: dict[str, PricingProvider] = {
        "fixed_per_day": FixedPerDayProvider(),
        "fixed_per_slot": FixedPerSlotProvider(),
        "per_hour": HourlyPricingProvider(),
        "tiered": TieredProvider(),
    }
    if model not in providers:
        raise ValueError(f"Unknown pricing model: {model}")
    return providers[model]
