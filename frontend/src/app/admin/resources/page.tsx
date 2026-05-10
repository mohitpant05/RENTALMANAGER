"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { redirect } from "next/navigation";
import api from "@/lib/api";
import type { ResourceTypeResponse } from "@/types/api";
import { TemplatePicker } from "@/components/resources/template-picker";
import { CreateTypeSheet } from "@/components/resources/create-type-sheet";
import { useCreateTypeSheetStore } from "@/lib/create-type-sheet-store";

export default function ResourcesPage() {
  const [showCustomSheet, setShowCustomSheet] = useState(false);
  const { open: typeSheetFromNav, setOpen: setTypeSheetFromNav } = useCreateTypeSheetStore();

  const typeSheetOpen = showCustomSheet || typeSheetFromNav;

  function closeTypeSheet() {
    setShowCustomSheet(false);
    setTypeSheetFromNav(false);
  }

  const { data: types, isLoading } = useQuery({
    queryKey: ["resource-types"],
    queryFn: async () => {
      const { data } = await api.get<ResourceTypeResponse[]>("/resource-types");
      return data;
    },
  });

  if (isLoading) {
    return (
      <div className="flex flex-1 items-center justify-center">
        <div className="h-8 w-8 animate-spin rounded-full border-2 border-primary border-t-transparent" />
      </div>
    );
  }

  if (types && types.length > 0) {
    redirect(`/admin/resources/${types[0].slug}`);
  }

  return (
    <>
      <TemplatePicker onCreateCustom={() => setShowCustomSheet(true)} />
      <CreateTypeSheet
        open={typeSheetOpen}
        onClose={closeTypeSheet}
      />
    </>
  );
}
