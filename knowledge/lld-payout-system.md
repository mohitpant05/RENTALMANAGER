# LLD: Payout System

## Overview

Tracks money owed to resource owners from completed, paid bookings. Admin creates payouts grouping unsettled bookings, then settles them.

Source: `backend/app/core/payouts/`

## Data Model

```sql
payouts (
  id             UUID PK,
  owner_id       UUID FK → users.id,
  amount         FLOAT,              -- sum of owner_payout for included bookings
  currency       VARCHAR(10),
  status         VARCHAR(20),        -- 'pending' | 'settled'
  period_start   TIMESTAMPTZ,        -- reporting period
  period_end     TIMESTAMPTZ,
  settled_at     TIMESTAMPTZ,
  settled_by     UUID,               -- admin who settled
  provider_ref   VARCHAR(255),       -- external payment reference
  notes          TEXT,
  created_at     TIMESTAMPTZ
)

payout_items (
  id             UUID PK,
  payout_id      UUID FK → payouts.id,
  booking_id     UUID FK → bookings.id,
  booking_total  FLOAT,              -- original booking total_price
  commission     FLOAT,              -- platform_commission taken
  owner_amount   FLOAT,              -- owner_payout for this booking
)
```

## Eligibility

A booking is "unsettled" when ALL of:
1. `booking.status = "completed"`
2. `payment.status = "paid"` (payment exists and is paid)
3. `booking.id` NOT IN any `payout_items` linked to a `settled` payout

## Owner Balance Calculation

`get_owner_balances()`:
```sql
SELECT resource.owner_id,
       SUM(booking.owner_payout) AS pending_amount,
       COUNT(booking.id) AS booking_count,
       booking.currency
FROM bookings
JOIN resources ON booking.resource_id = resource.id
JOIN payments ON payment.booking_id = booking.id
WHERE booking.status = 'completed'
  AND payment.status = 'paid'
  AND booking.id NOT IN (
    SELECT payout_items.booking_id
    FROM payout_items JOIN payouts ON payout_items.payout_id = payouts.id
    WHERE payouts.status = 'settled'
  )
GROUP BY resource.owner_id, booking.currency
```

Returns per-owner: pending_amount, booking_count, currency, last settled date.

## Payout Flow

### Create Payout
```
1. Admin specifies: owner_id, period_start, period_end, currency
2. Query unsettled bookings for owner within period + currency
3. If none → 400 "No unsettled bookings"
4. Sum owner_payout across bookings → payout.amount
5. Create Payout (status="pending")
6. Create PayoutItem per booking (booking_total, commission, owner_amount)
```

### Settle Payout
```
1. Validate payout exists and status == "pending" (409 otherwise)
2. Set status = "settled", settled_at = now, settled_by = admin_id
```

## State Machine

```
create_payout() → pending → settle_payout() → settled
```

No cancel/void flow exists yet.

## Money Flow Summary

```
Customer pays:    customer_total = total_price + service_fee
Platform keeps:   platform_commission (from owner) + service_fee (from customer)
Owner receives:   owner_payout = total_price - platform_commission
Payout tracks:    sum of owner_payout for settled bookings in period
```
