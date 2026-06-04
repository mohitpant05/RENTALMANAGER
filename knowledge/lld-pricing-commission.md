# LLD: Pricing & Commission Calculation

## Pricing Models

Source: `backend/app/domains/resources/pricing/providers.py`

Each ResourceType has a `pricing_model` field selecting the strategy.

### fixed_per_day
```
price = base_price × ceil(duration_seconds / 86400)
minimum = base_price × 1
```

### fixed_per_slot
```
price = base_price (flat, regardless of duration)
```

### per_hour
```
price = base_price × ceil(duration_seconds / 3600)
minimum = base_price × 1
```

### tiered (volume discount)
```
Config:
{
  "tiers": [
    { "min_days": 1, "max_days": 7, "rate_multiplier": 1.0 },
    { "min_days": 8, "max_days": 30, "rate_multiplier": 0.9 },
    { "min_days": 31, "rate_multiplier": 0.8 }
  ]
}

Algorithm:
1. total_days = ceil(duration / 86400), minimum 1
2. Sort tiers by min_days ascending
3. For each tier:
   - Calculate tier_span = max_days - min_days + 1 (or remaining if no max)
   - days_in_tier = min(remaining_days, tier_span)
   - total += days_in_tier × base_price × rate_multiplier
   - remaining -= days_in_tier
4. Any remaining days charged at base_price × 1.0
5. Round to 2 decimals

Example (base_price=100, 15 days):
  Tier 1: 7 days × 100 × 1.0 = 700
  Tier 2: 8 days × 100 × 0.9 = 720
  Total: 1420.00
```

## Commission System

Source: `backend/app/core/commission/service.py`, `schemas.py`

### Commission Config
```json
{
  "owner_percent": 10.0,
  "owner_fixed": 0.0,
  "customer_percent": 5.0,
  "customer_fixed": 2.0,
  "currency": "USD"
}
```

### Resolution Order (waterfall)
```
Resource.commission_config → ResourceType.commission_config → null (no commission)
```
Resource-level overrides type-level.

### Breakdown Calculation
```
Input: total_price, commission_config

platform_commission = (total_price × owner_percent / 100) + owner_fixed
service_fee         = (total_price × customer_percent / 100) + customer_fixed
owner_payout        = total_price - platform_commission
customer_total      = total_price + service_fee
```

All values rounded to 2 decimals.

### Example
```
total_price = 500.00
config = { owner_percent: 10, owner_fixed: 5, customer_percent: 5, customer_fixed: 2 }

platform_commission = (500 × 10 / 100) + 5 = 55.00
service_fee         = (500 × 5 / 100) + 2  = 27.00
owner_payout        = 500 - 55              = 445.00
customer_total      = 500 + 27              = 527.00
```

If no commission config: service_fee=0, platform_commission=0, owner_payout=total_price, customer_total=total_price.

### Booking Integration

When booking created:
1. `get_pricing_provider(pricing_model).calculate(base_price, start, end, pricing_config)` → total_price
2. `resolve_commission(session, resource_id)` → CommissionConfig (resource → type → null)
3. `calculate_breakdown(total_price, currency, config)` → breakdown dict
4. All values stored on Booking model: `total_price`, `service_fee`, `platform_commission`, `owner_payout`, `customer_total`
