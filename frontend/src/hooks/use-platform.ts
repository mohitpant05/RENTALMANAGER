"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import axios from "axios";
import { usePlatformStore } from "@/lib/platform-store";

function platformApi() {
  const token = usePlatformStore.getState().token;
  return axios.create({
    baseURL: "/api/platform",
    headers: token ? { Authorization: `Bearer ${token}` } : {},
  });
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

export interface DashboardStats {
  total_tenants: number;
  active_tenants: number;
  inactive_tenants: number;
  total_users: number;
  total_bookings: number;
  services: Record<string, { status: string; detail?: string }>;
}

export interface PlatformSetting {
  id: string;
  key: string;
  value: string;
  description: string | null;
  updated_at: string;
}

export interface ThemeResponse {
  id: string;
  tenant_id: string;
  brand: Record<string, unknown>;
  colors: Record<string, string>;
  typography: Record<string, unknown>;
  components: Record<string, unknown>;
  features: Record<string, unknown>;
  updated_at: string;
}

export function usePlatformLogin() {
  const { setToken } = usePlatformStore();
  return useMutation({
    mutationFn: async (data: { email: string; password: string }) => {
      const res = await platformApi().post("/login", data);
      return res.data as { access_token: string };
    },
    onSuccess: (data) => {
      setToken(data.access_token);
    },
  });
}

export function useValidateKey() {
  return useMutation({
    mutationFn: async (key: string) => {
      const res = await axios.post("/api/platform/validate-key", { key });
      return res.data as { valid: boolean };
    },
  });
}

export function useDashboardStats() {
  return useQuery({
    queryKey: ["platform", "dashboard"],
    queryFn: async () => {
      const res = await platformApi().get("/dashboard/stats");
      return res.data as DashboardStats;
    },
    refetchInterval: 60_000,
  });
}

export function useTenants() {
  return useQuery({
    queryKey: ["platform", "tenants"],
    queryFn: async () => {
      const res = await platformApi().get("/tenants");
      return res.data as TenantResponse[];
    },
  });
}

export function useTenant(id: string) {
  return useQuery({
    queryKey: ["platform", "tenants", id],
    queryFn: async () => {
      const res = await platformApi().get(`/tenants/${id}`);
      return res.data as TenantResponse;
    },
    enabled: !!id,
  });
}

export function useCreateTenant() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (data: { name: string; slug: string; base_currency?: string; timezone?: string }) => {
      const res = await platformApi().post("/tenants", data);
      return res.data as TenantResponse;
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ["platform", "tenants"] }),
  });
}

export function useToggleTenant() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, activate }: { id: string; activate: boolean }) => {
      const action = activate ? "activate" : "deactivate";
      const res = await platformApi().post(`/tenants/${id}/${action}`);
      return res.data as TenantResponse;
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ["platform", "tenants"] }),
  });
}

export function usePlatformSettings() {
  return useQuery({
    queryKey: ["platform", "settings"],
    queryFn: async () => {
      const res = await platformApi().get("/settings");
      return res.data as PlatformSetting[];
    },
  });
}

export function useUpsertSetting() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ key, value, description }: { key: string; value: string; description?: string }) => {
      const res = await platformApi().put(`/settings/${key}`, { value, description });
      return res.data as PlatformSetting;
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ["platform", "settings"] }),
  });
}

export function useTenantTheme(tenantId: string) {
  return useQuery({
    queryKey: ["platform", "tenants", tenantId, "theme"],
    queryFn: async () => {
      const res = await platformApi().get(`/tenants/${tenantId}/theme`);
      return res.data as ThemeResponse;
    },
    enabled: !!tenantId,
  });
}

export interface DomainResponse {
  id: string;
  tenant_id: string;
  domain: string;
  is_primary: boolean;
  is_verified: boolean;
  created_at: string;
}

export function useTenantDomains(tenantId: string) {
  return useQuery({
    queryKey: ["platform", "tenants", tenantId, "domains"],
    queryFn: async () => {
      const res = await platformApi().get(`/tenants/${tenantId}/domains`);
      return res.data as DomainResponse[];
    },
    enabled: !!tenantId,
  });
}

export function useAddTenantDomain(tenantId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (data: { domain: string; is_primary?: boolean }) => {
      const res = await platformApi().post(`/tenants/${tenantId}/domains`, data);
      return res.data as DomainResponse;
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ["platform", "tenants", tenantId, "domains"] }),
  });
}

export function useDeleteTenantDomain(tenantId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (domainId: string) => {
      await platformApi().delete(`/tenants/${tenantId}/domains/${domainId}`);
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ["platform", "tenants", tenantId, "domains"] }),
  });
}
