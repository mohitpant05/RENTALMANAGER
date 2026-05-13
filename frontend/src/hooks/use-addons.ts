"use client";

import { useCallback, useState } from "react";
import api from "@/lib/api";
import type {
  AddAddonRequest,
  AddonTypeGroup,
  BookingGroupResponse,
  BookingItemCreate,
  BookingResponse,
  BundledBookingCreate,
  ResourceAssignmentCreate,
  ResourceAssignmentResponse,
  ResourceAssignmentUpdate,
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
    listAssignments,
    createAssignment,
    updateAssignment,
    deleteAssignment,
  };
}
