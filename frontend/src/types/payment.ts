export interface PaymentResponse {
  id: string;
  booking_id: string;
  amount: number;
  currency: string;
  provider: string;
  status: string;
  provider_ref: string | null;
  paid_at: string | null;
  refund_amount: number | null;
  refunded_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface MarkPaidRequest {
  notes?: string;
}

export interface RefundRequest {
  amount?: number;
  reason?: string;
}
