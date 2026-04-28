import math
from datetime import datetime


class FixedPerDayProvider:
    def calculate(
        self, base_price: float, start: datetime, end: datetime, config: dict | None
    ) -> float:
        days = math.ceil((end - start).total_seconds() / 86400)
        return base_price * max(days, 1)


class FixedPerSlotProvider:
    def calculate(
        self, base_price: float, start: datetime, end: datetime, config: dict | None
    ) -> float:
        return base_price


class HourlyPricingProvider:
    def calculate(
        self, base_price: float, start: datetime, end: datetime, config: dict | None
    ) -> float:
        hours = math.ceil((end - start).total_seconds() / 3600)
        return base_price * max(hours, 1)


class TieredProvider:
    def calculate(
        self, base_price: float, start: datetime, end: datetime, config: dict | None
    ) -> float:
        total_days = math.ceil((end - start).total_seconds() / 86400)
        total_days = max(total_days, 1)
        if not config or "tiers" not in config:
            return base_price * total_days

        tiers = sorted(config["tiers"], key=lambda t: t["min_days"])
        total = 0.0
        remaining = total_days

        for tier in tiers:
            min_d = tier["min_days"]
            max_d = tier.get("max_days")
            multiplier = tier.get("rate_multiplier", 1.0)

            if remaining <= 0:
                break

            if max_d is None:
                days_in_tier = remaining
            else:
                tier_span = max_d - min_d + 1
                days_in_tier = min(remaining, tier_span)

            total += days_in_tier * base_price * multiplier
            remaining -= days_in_tier

        if remaining > 0:
            total += remaining * base_price

        return round(total, 2)
