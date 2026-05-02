import { create } from "zustand";

interface CreateTypeSheetStore {
  open: boolean;
  setOpen: (open: boolean) => void;
}

export const useCreateTypeSheetStore = create<CreateTypeSheetStore>((set) => ({
  open: false,
  setOpen: (open) => set({ open }),
}));
