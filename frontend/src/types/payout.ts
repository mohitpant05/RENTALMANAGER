export interface PayoutItemResponse {
  id: string;
  payout_id: string;
  booking_id: string;
  booking_total: number;
  commission: number;
  owner_amount: number;
}

export interface PayoutResponse {
  id: string;
  owner_id: string;
  amount: number;
  currency: string;
  status: string;
  period_start: string | null;
  period_end: string | null;
  settled_at: string | null;
  settled_by: string | null;
  provider_ref: string | null;
  notes: string | null;
  created_at: string;
  items: PayoutItemResponse[];
}

export interface PayoutCreate {
  owner_id: string;
  period_start: string;
  period_end: string;
  currency: string;
  notes?: string;
}

export interface OwnerBalance {
  owner_id: string;
  owner_name: string;
  owner_email: string;
  pending_amount: number;
  currency: string;
  booking_count: number;
  last_settled: string | null;
}

export interface DeactivationImpact {
  resources_count: number;
  pending_bookings_count: number;
}
