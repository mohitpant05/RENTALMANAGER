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
  preferred_currency: string;
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

export type ResourceTypeRole = "primary" | "addon" | "standalone" | "hidden";

export const VALID_RESOURCE_TYPE_ROLES: ResourceTypeRole[] = [
  "primary",
  "addon",
  "standalone",
  "hidden",
];

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
  role: string;
  discovery_radius_km: number | null;
  display_order: number;
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
  role?: string;
  discovery_radius_km?: number | null;
  display_order?: number;
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
  role?: string;
  discovery_radius_km?: number | null;
  display_order?: number;
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
  support_contact_id: string | null;
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
  support_contact_id?: string;
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
  support_contact_id?: string;
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
  service_fee: number;
  platform_commission: number;
  owner_payout: number;
  customer_total: number;
  hold_token: string | null;
  cancellation_policy: Record<string, unknown> | null;
  notes: string | null;
  auto_confirm: boolean;
  parent_booking_id: string | null;
  booking_group_id: string | null;
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
  user_id?: string;
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

// ─── Staff ─────────────────────────────────────────────

export interface StaffInviteRequest {
  email: string;
  full_name: string;
  user_type: "staff" | "admin";
  role_slugs?: string[];
}

export interface StaffUserResponse {
  id: string;
  email: string;
  full_name: string;
  phone: string | null;
  is_active: boolean;
  user_type: string;
  created_at: string;
  roles: string[];
}

// ─── Notifications ─────────────────────────────────────

export interface NotificationResponse {
  id: string;
  user_id: string;
  event_type: string;
  payload: Record<string, unknown>;
  message: string;
  is_read: boolean;
  created_at: string;
}

export interface UnreadCountResponse {
  count: number;
}

// ─── Reviews ───────────────────────────────────────────

export interface ReviewResponse {
  id: string;
  resource_id: string | null;
  lister_id: string | null;
  reviewer_id: string;
  direction: string;
  rating: number;
  comment: string | null;
  category_ratings: Record<string, number> | null;
  status: string;
  rejection_reason: string | null;
  created_at: string;
  updated_at: string;
}

export interface ReviewCreate {
  resource_id: string;
  rating: number;
  comment?: string;
  category_ratings?: Record<string, number>;
  direction?: string;
}

export interface ReviewModerateRequest {
  status: "approved" | "rejected";
  rejection_reason?: string;
}

export interface RatingSummaryResponse {
  average: number;
  count: number;
  distribution: Record<string, number>;
}

// ─── Storage ───────────────────────────────────────────

export interface UploadUrlRequest {
  filename: string;
  content_type: string;
  entity_type: string;
  entity_id: string;
}

export interface UploadUrlResponse {
  upload_url: string;
  attachment_id: string;
}

export interface AttachmentResponse {
  id: string;
  entity_type: string;
  entity_id: string;
  filename: string;
  content_type: string;
  size_bytes: number;
  url: string;
  created_at: string;
}

// ─── Search ────────────────────────────────────────────

export interface SearchRequest {
  q: string;
  resource_type_slug?: string;
  filters?: Record<string, unknown>;
  geo_lat?: number;
  geo_lng?: number;
  geo_radius_km?: number;
  sort_by?: string;
  sort_order?: "asc" | "desc";
  offset?: number;
  limit?: number;
}

export interface SearchHit {
  id: string;
  name: string;
  description: string;
  location_address: string;
  base_price: number;
  currency: string;
  status: string;
  rating_avg: number;
  rating_count: number;
  type_slug: string;
  geo: { lat: number; lng: number } | null;
  attributes: Record<string, unknown> | null;
}

export interface SearchResponse {
  hits: SearchHit[];
  query: string;
  processing_time_ms: number;
  estimated_total_hits: number;
  offset: number;
  limit: number;
}

// ─── Domains ───────────────────────────────────────────

export interface DomainResponse {
  id: string;
  domain: string;
  tenant_id: string;
  is_primary: boolean;
  is_verified: boolean;
  created_at: string;
}

export interface DomainCreate {
  domain: string;
}

// ─── Bundled Bookings & Addons ─────────────────────────

export interface BookingItemCreate {
  resource_id: string;
  hold_token: string;
  start_time: string;
  end_time: string;
  notes?: string;
  auto_confirm?: boolean;
}

export interface BundledBookingCreate {
  primary: BookingItemCreate;
  addons: BookingItemCreate[];
}

export interface AddAddonRequest {
  resource_id: string;
  hold_token: string;
  start_time: string;
  end_time: string;
  notes?: string;
  auto_confirm?: boolean;
}

export interface BookingGroupResponse {
  group_id: string;
  primary: BookingResponse;
  addons: BookingResponse[];
}

export interface AddonResourceItem {
  id: string;
  name: string;
  description: string | null;
  base_price: number;
  currency: string;
  rating_avg: number;
  rating_count: number;
  distance_km: number | null;
  is_assigned: boolean;
  available: boolean;
  location_address: string | null;
  attributes: Record<string, unknown> | null;
}

export interface AddonTypeGroup {
  type_name: string;
  type_slug: string;
  resources: AddonResourceItem[];
}

// ─── Resource Assignments ──────────────────────────────

export interface ResourceAssignmentResponse {
  id: string;
  primary_resource_id: string;
  addon_resource_id: string;
  priority: number;
  assigned_by: string;
  created_at: string;
  updated_at: string;
}

export interface ResourceAssignmentCreate {
  addon_resource_id: string;
  priority?: number;
}

export interface ResourceAssignmentUpdate {
  priority: number;
}
