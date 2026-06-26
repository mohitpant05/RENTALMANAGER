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
  meeting_link: string | null;
  created_at: string;
}

export interface CalendarSlot {
  start: string;
  end: string;
  status: "available" | "booked" | "blocked";
  booking: DemoRequest | null;
}

export interface SlotBlock {
  id: string;
  slot_time: string;
  specific_date: string | null;
  action: "block" | "unblock";
  created_at: string;
}

export function useAvailableSlots(enabled = true) {
  return useQuery({
    queryKey: ["demo-slots"],
    queryFn: async () => {
      const res = await publicApi.get("/slots");
      return res.data as DemoSlot[];
    },
    enabled,
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

export function useDemoCalendar() {
  return useQuery({
    queryKey: ["platform", "demo-calendar"],
    queryFn: async () => {
      const res = await platformApi().get("/calendar");
      return res.data as CalendarSlot[];
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
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["platform", "demo-requests"] });
      qc.invalidateQueries({ queryKey: ["platform", "demo-calendar"] });
    },
  });
}

export function useSlotBlocks() {
  return useQuery({
    queryKey: ["platform", "slot-blocks"],
    queryFn: async () => {
      const res = await platformApi().get("/slot-blocks");
      return res.data as SlotBlock[];
    },
  });
}

export function useCreateSlotBlock() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (data: {
      slot_time: string;
      specific_date?: string | null;
      action: "block" | "unblock";
    }) => {
      const res = await platformApi().post("/slot-blocks", data);
      return res.data as SlotBlock;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["platform", "slot-blocks"] });
      qc.invalidateQueries({ queryKey: ["platform", "demo-calendar"] });
      qc.invalidateQueries({ queryKey: ["demo-slots"] });
    },
  });
}

export function useDeleteSlotBlock() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (id: string) => {
      await platformApi().delete(`/slot-blocks/${id}`);
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["platform", "slot-blocks"] });
      qc.invalidateQueries({ queryKey: ["platform", "demo-calendar"] });
      qc.invalidateQueries({ queryKey: ["demo-slots"] });
    },
  });
}
