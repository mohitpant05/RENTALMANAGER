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

export interface RefundPendingItem {
  booking_id: string;
  payment_id: string;
  customer_name: string;
  customer_email: string;
  resource_name: string;
  cancelled_at: string | null;
  start_time: string;
  booking_amount: number;
  currency: string;
  refund_percent: number;
  refund_amount: number;
  payment_status: string;
  provider: string;
}

export interface RefundSettleRequest {
  payment_id: string;
  override_percent?: number | null;
}

export interface RefundSettleResult {
  payment_id: string;
  success: boolean;
  refund_amount: number | null;
  error: string | null;
}

export interface BulkRefundSettleResponse {
  results: RefundSettleResult[];
  settled_count: number;
  failed_count: number;
}
