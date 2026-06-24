"use client";

import { useCallback, useState } from "react";
import api from "@/lib/api";
import type {
  AddAddonRequest,
  AddonSchedule,
  AddonTypeGroup,
  BookingGroupResponse,
  BookingItemCreate,
  BookingResponse,
  BundledBookingCreate,
  HoldResponse,
  ResourceAssignmentCreate,
  ResourceAssignmentResponse,
  ResourceAssignmentUpdate,
  SchedulesCheckResponse,
} from "@/types/api";
import { toast } from "sonner";

export function useAddons() {
  const [loading, setLoading] = useState(false);

  const discoverAddons = useCallback(
    async (
      resourceId: string,
      startDate: string,
      endDate: string,
    ): Promise<Record<string, AddonTypeGroup>> => {
      setLoading(true);
      try {
        const { data } = await api.get<Record<string, AddonTypeGroup>>(
          `/resources/${resourceId}/addons`,
          { params: { start_date: startDate, end_date: endDate } },
        );
        return data;
      } catch {
        toast.error("Failed to discover addons");
        return {};
      } finally {
        setLoading(false);
      }
    },
    [],
  );

  const createBundledBooking = useCallback(
    async (payload: BundledBookingCreate): Promise<BookingGroupResponse | null> => {
      setLoading(true);
      try {
        const { data } = await api.post<BookingGroupResponse>("/bookings/bundled", payload);
        toast.success("Bundled booking confirmed!");
        return data;
      } catch {
        toast.error("Failed to create bundled booking");
        return null;
      } finally {
        setLoading(false);
      }
    },
    [],
  );

  const addAddonToBooking = useCallback(
    async (bookingId: string, payload: AddAddonRequest): Promise<BookingResponse | null> => {
      setLoading(true);
      try {
        const { data } = await api.post<BookingResponse>(
          `/bookings/${bookingId}/add-addon`,
          payload,
        );
        toast.success("Addon added to booking!");
        return data;
      } catch {
        toast.error("Failed to add addon");
        return null;
      } finally {
        setLoading(false);
      }
    },
    [],
  );

  const listAssignments = useCallback(
    async (resourceId: string): Promise<ResourceAssignmentResponse[]> => {
      setLoading(true);
      try {
        const { data } = await api.get<ResourceAssignmentResponse[]>(
          `/resources/${resourceId}/assignments`,
        );
        return data;
      } catch {
        toast.error("Failed to load assignments");
        return [];
      } finally {
        setLoading(false);
      }
    },
    [],
  );

  const createAssignment = useCallback(
    async (
      resourceId: string,
      payload: ResourceAssignmentCreate,
    ): Promise<ResourceAssignmentResponse | null> => {
      setLoading(true);
      try {
        const { data } = await api.post<ResourceAssignmentResponse>(
          `/resources/${resourceId}/assignments`,
          payload,
        );
        toast.success("Assignment created");
        return data;
      } catch {
        toast.error("Failed to create assignment");
        return null;
      } finally {
        setLoading(false);
      }
    },
    [],
  );

  const updateAssignment = useCallback(
    async (
      resourceId: string,
      assignmentId: string,
      payload: ResourceAssignmentUpdate,
    ): Promise<ResourceAssignmentResponse | null> => {
      setLoading(true);
      try {
        const { data } = await api.patch<ResourceAssignmentResponse>(
          `/resources/${resourceId}/assignments/${assignmentId}`,
          payload,
        );
        return data;
      } catch {
        toast.error("Failed to update assignment");
        return null;
      } finally {
        setLoading(false);
      }
    },
    [],
  );

  const checkSchedules = useCallback(
    async (
      resourceId: string,
      schedules: AddonSchedule[],
      availabilityModel: string,
    ): Promise<boolean> => {
      try {
        const { data } = await api.post<SchedulesCheckResponse>(
          `/resources/${resourceId}/availability/check-schedules`,
          { schedules, availability_model: availabilityModel },
        );
        if (!data.available) {
          const unavailable = data.schedule_states
            .filter((s) => !s.available)
            .map((s) => `${s.date} ${s.start_time ?? ""} ${s.end_time ?? ""}`.trim());
          toast.error(`Unavailable slots: ${unavailable.join(", ")}`);
        }
        return data.available;
      } catch {
        toast.error("Failed to check schedule availability");
        return false;
      }
    },
    [],
  );

  const holdAndAddAddon = useCallback(
    async (
      bookingId: string,
      resourceId: string,
      startTime: string,
      endTime: string,
      schedules: AddonSchedule[] | undefined,
      availabilityModel?: string,
    ): Promise<BookingResponse | null> => {
      setLoading(true);
      try {
        let holdTokens: string[] = [];
        let holdFailed = false;

        try {
          if (availabilityModel === "time_slot" && schedules && schedules.length > 0) {
            for (const s of schedules) {
              const slotStart = `${s.date}T${s.start_time ?? "00:00"}:00Z`;
              const slotEnd = `${s.date}T${s.end_time ?? "23:59"}:00Z`;
              const { data: hold } = await api.post<HoldResponse>(
                `/resources/${resourceId}/availability/hold`,
                { start: slotStart, end: slotEnd },
              );
              holdTokens.push(hold.hold_token);
            }
          } else {
            const { data: hold } = await api.post<HoldResponse>(
              `/resources/${resourceId}/availability/hold`,
              { start: startTime, end: endTime },
            );
            holdTokens = [hold.hold_token];
          }
        } catch {
          holdFailed = true;
        }

        const payload: AddAddonRequest = {
          resource_id: resourceId,
          hold_token: holdFailed ? "" : holdTokens[0],
          hold_tokens: !holdFailed && holdTokens.length > 1 ? holdTokens : undefined,
          start_time: startTime,
          end_time: endTime,
          schedules,
          timezone: Intl.DateTimeFormat().resolvedOptions().timeZone,
        };

        const { data: booking } = await api.post<BookingResponse>(
          `/bookings/${bookingId}/add-addon`,
          payload,
        );
        toast.success("Addon added to booking!");
        return booking;
      } catch {
        toast.error("Failed to add addon");
        return null;
      } finally {
        setLoading(false);
      }
    },
    [],
  );

  const deleteAssignment = useCallback(
    async (resourceId: string, assignmentId: string): Promise<boolean> => {
      setLoading(true);
      try {
        await api.delete(`/resources/${resourceId}/assignments/${assignmentId}`);
        toast.success("Assignment removed");
        return true;
      } catch {
        toast.error("Failed to delete assignment");
        return false;
      } finally {
        setLoading(false);
      }
    },
    [],
  );

  return {
    loading,
    discoverAddons,
    createBundledBooking,
    addAddonToBooking,
    checkSchedules,
    holdAndAddAddon,
    listAssignments,
    createAssignment,
    updateAssignment,
    deleteAssignment,
  };
}
