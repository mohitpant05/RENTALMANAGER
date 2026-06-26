"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import axios from "axios";
import { usePlatformStore } from "@/lib/platform-store";

function platformApi() {
  const token = usePlatformStore.getState().token;
  return axios.create({
    baseURL: "/api/demo-requests",
    headers: token ? { Authorization: `Bearer ${token}` } : {},
  });
}

const publicApi = axios.create({ baseURL: "/api/demo-requests" });

export interface DemoSlot {
  start: string;
  end: string;
}

export interface DemoRequest {
  id: string;
  name: string;
  email: string;
  company: string | null;
  message: string | null;
  slot_start: string;
  slot_end: string;
  status: "pending" | "confirmed" | "completed" | "cancelled";
  created_at: string;
}

export function useAvailableSlots() {
  return useQuery({
    queryKey: ["demo-slots"],
    queryFn: async () => {
      const res = await publicApi.get("/slots");
      return res.data as DemoSlot[];
    },
  });
}

export function useSubmitDemoRequest() {
  return useMutation({
    mutationFn: async (data: {
      name: string;
      email: string;
      company?: string;
      message?: string;
      slot_start: string;
    }) => {
      const res = await publicApi.post("", data);
      return res.data as DemoRequest;
    },
  });
}

export function useDemoRequests() {
  return useQuery({
    queryKey: ["platform", "demo-requests"],
    queryFn: async () => {
      const res = await platformApi().get("");
      return res.data as DemoRequest[];
    },
  });
}

export function useUpdateDemoStatus() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, status }: { id: string; status: string }) => {
      const res = await platformApi().patch(`/${id}/status`, { status });
      return res.data as DemoRequest;
    },
    onSuccess: () =>
      qc.invalidateQueries({ queryKey: ["platform", "demo-requests"] }),
  });
}
