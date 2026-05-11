export interface CommissionConfig {
  owner_percent: number;
  owner_fixed: number;
  customer_percent: number;
  customer_fixed: number;
  currency: string;
}

export interface CommissionConfigResponse {
  entity_type: string;
  entity_id: string;
  config: CommissionConfig | null;
  inherited_from: string | null;
}

export interface CommissionConfigUpdate {
  owner_percent?: number;
  owner_fixed?: number;
  customer_percent?: number;
  customer_fixed?: number;
  currency?: string;
}

export interface CommissionPreview {
  amount: number;
  currency: string;
  config: CommissionConfig | null;
  service_fee: number;
  platform_commission: number;
  owner_payout: number;
  customer_total: number;
}
