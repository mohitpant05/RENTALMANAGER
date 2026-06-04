# LLD: Payment System

## Architecture

Provider pattern with pluggable payment backends. Provider selected from tenant config.

Source: `backend/app/core/payments/`

## Provider Selection

```python
config = tenant.config or {}
provider_name = config.get("payment_provider", "manual")  # default: manual
```

Tenant config JSONB determines active provider per tenant.

## Provider Interface

```python
class PaymentProvider(Protocol):
    async def create_payment(amount, currency, metadata) -> PaymentResult
    async def refund_payment(provider_ref, amount) -> RefundResult
```

## Available Providers

### Manual (`providers/manual.py`)
- `create_payment`: always succeeds, no external call
- `refund_payment`: always succeeds
- Use case: offline payments, cash, bank transfer

### Stripe (`providers/stripe.py`)
- `create_payment`: creates Stripe PaymentIntent
- `refund_payment`: creates Stripe Refund
- Config: `stripe_secret_key` in tenant config

### Razorpay (`providers/razorpay.py`)
- `create_payment`: creates Razorpay Order
- `refund_payment`: creates Razorpay Refund
- Config: `razorpay_key_id`, `razorpay_key_secret` in tenant config

## Payment Model

```sql
payments (
  id              UUID PK,
  booking_id      UUID FK → bookings.id (UNIQUE),
  amount          FLOAT,
  currency        VARCHAR(10),
  provider        VARCHAR(20),          -- 'manual' | 'stripe' | 'razorpay'
  status          VARCHAR(30),          -- see state machine below
  provider_ref    VARCHAR(255),         -- external payment ID
  provider_data   JSONB,                -- provider-specific response data
  paid_at         TIMESTAMPTZ,
  refund_amount   FLOAT,
  refunded_at     TIMESTAMPTZ,
  created_at      TIMESTAMPTZ,
  updated_at      TIMESTAMPTZ
)
```

One payment per booking (unique constraint on booking_id).

## Payment State Machine

```
create_payment()
  │
  ▼
┌──────────┐    mark_paid()     ┌──────────┐
│ pending  │───────────────────►│   paid   │
└──────────┘                    └────┬─────┘
  │                                  │
  │ (provider failure)               │ refund_payment()
  ▼                                  │
┌──────────┐                    ┌────▼──────────────┐
│  failed  │                    │ refunded /         │
└──────────┘                    │ partially_refunded │
                                └───────────────────┘
```

## Flows

### Create Payment
```
1. Validate booking exists (404)
2. Check no existing payment for booking (409)
3. Get provider from tenant config
4. Call provider.create_payment(customer_total, currency, {booking_id})
5. Create Payment record: status = "pending" (or "failed")
6. Store provider_ref + provider_data
```

### Mark Paid (admin only)
```
1. Load payment (404)
2. Validate status == "pending" (409)
3. Set status = "paid", paid_at = now
```

### Refund (admin only)
```
1. Load payment (404)
2. Validate status == "paid" (409)
3. If amount specified, validate ≤ payment amount (400)
4. If no amount, full refund
5. Call provider.refund_payment(provider_ref, amount)
6. If provider fails → 502
7. Set refund_amount, refunded_at
8. Status = "refunded" (full) or "partially_refunded"
```

## Amount Flow

```
Pricing:     total_price (resource × duration)
Commission:  + service_fee → customer_total
Payment:     charges customer_total
Payout:      owner receives owner_payout (total_price - platform_commission)
```

## Webhook Endpoint

`/api/payments/webhook/` — tenant-free path (no X-Tenant-ID required).
For Stripe/Razorpay webhook callbacks to confirm payments externally.
