export interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
}

export interface UserResponse {
  id: string;
  email: string;
  full_name: string;
  phone: string | null;
  is_active: boolean;
  is_verified: boolean;
  user_type: string;
  avatar_url: string | null;
  created_at: string;
  roles: string[];
}

export interface LoginRequest {
  email: string;
  password: string;
}

export interface RegisterRequest {
  email: string;
  password: string;
  full_name: string;
  phone?: string;
}

export interface RefreshRequest {
  refresh_token: string;
}

export interface TenantResponse {
  id: string;
  name: string;
  slug: string;
  schema_name: string;
  is_active: boolean;
  config: Record<string, unknown> | null;
  base_currency: string;
  timezone: string;
  created_at: string;
  updated_at: string;
}

export interface ThemeResponse {
  id: string;
  tenant_id: string;
  brand: Record<string, unknown>;
  colors: Record<string, unknown>;
  typography: Record<string, unknown>;
  components: Record<string, unknown>;
  features: Record<string, unknown>;
  updated_at: string;
}

export interface AcceptInviteRequest {
  token: string;
  password: string;
}

export interface VerifyInviteResponse {
  valid: boolean;
  email?: string;
  full_name?: string;
}

export interface ResourceTypeResponse {
  id: string;
  name: string;
  slug: string;
  icon: string | null;
  description: string | null;
  availability_model: string;
  pricing_model: string;
  attribute_schema: AttributeField[] | null;
  slot_config: Record<string, unknown> | null;
  pricing_config: Record<string, unknown> | null;
  cancellation_defaults: Record<string, unknown> | null;
  requires_verification: boolean;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface AttributeField {
  name: string;
  type: "enum" | "number" | "boolean" | "tags" | "text";
  options?: string[];
  required?: boolean;
  filterable?: boolean;
}

export interface ResourceTypeCreate {
  name: string;
  slug: string;
  icon?: string;
  description?: string;
  availability_model: string;
  pricing_model: string;
  attribute_schema?: AttributeField[];
  slot_config?: Record<string, unknown>;
  pricing_config?: Record<string, unknown>;
  cancellation_defaults?: Record<string, unknown>;
  requires_verification?: boolean;
}

export interface ResourceTypeUpdate {
  name?: string;
  slug?: string;
  icon?: string;
  description?: string;
  attribute_schema?: AttributeField[];
  slot_config?: Record<string, unknown>;
  pricing_config?: Record<string, unknown>;
  cancellation_defaults?: Record<string, unknown>;
  requires_verification?: boolean;
  is_active?: boolean;
}

export interface ResourceTypeTemplate {
  slug: string;
  name: string;
  description?: string;
}

export interface ResourceResponse {
  id: string;
  type_id: string;
  name: string;
  description: string | null;
  location_lat: number | null;
  location_lng: number | null;
  location_address: string | null;
  attributes: Record<string, unknown> | null;
  base_price: number;
  currency: string;
  status: string;
  rating_avg: number;
  rating_count: number;
  owner_id: string;
  version: number;
  created_at: string;
  updated_at: string;
}

export interface ResourceCreate {
  type_id: string;
  name: string;
  description?: string;
  location_lat?: number;
  location_lng?: number;
  location_address?: string;
  attributes?: Record<string, unknown>;
  base_price: number;
  currency?: string;
}

export interface ResourceUpdate {
  name?: string;
  description?: string;
  location_lat?: number;
  location_lng?: number;
  location_address?: string;
  attributes?: Record<string, unknown>;
  base_price?: number;
  currency?: string;
  status?: string;
}

// ─── Bookings ───────────────────────────────────────────

export interface BookingResponse {
  id: string;
  resource_id: string;
  user_id: string;
  status: string;
  start_time: string;
  end_time: string;
  total_price: number;
  currency: string;
  hold_token: string | null;
  cancellation_policy: Record<string, unknown> | null;
  notes: string | null;
  auto_confirm: boolean;
  confirmed_at: string | null;
  cancelled_at: string | null;
  cancellation_reason: string | null;
  refund_percent: number | null;
  version: number;
  created_at: string;
  updated_at: string;
}

export interface BookingCreate {
  resource_id: string;
  hold_token: string;
  start_time: string;
  end_time: string;
  notes?: string;
  auto_confirm?: boolean;
}

export interface BookingCancel {
  reason?: string;
}

export interface BookingReject {
  reason?: string;
}

// ─── Availability ───────────────────────────────────────

export interface AvailabilityCheckRequest {
  start: string;
  end: string;
}

export interface AvailabilityCheckResponse {
  available: boolean;
  price: number | null;
}

export interface HoldRequest {
  start: string;
  end: string;
  hold_minutes?: number;
}

export interface HoldResponse {
  hold_token: string;
  expires: string;
  price: number;
}

export interface ReleaseRequest {
  hold_token: string;
}

export interface PriceCalculateRequest {
  start: string;
  end: string;
}

export interface PriceCalculateResponse {
  price: number;
  currency: string;
}
