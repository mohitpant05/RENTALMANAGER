"use client";

import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { useMutation } from "@tanstack/react-query";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { toast } from "sonner";
import api from "@/lib/api";
import { useAuthStore } from "@/lib/auth-store";
import { useCurrencyStore, useSupportedCurrencies } from "@/hooks/use-currency";
import type { UserResponse } from "@/types/api";

const phoneSchema = z
  .string()
  .refine((v) => !v || /^\+?\d{7,15}$/.test(v), {
    message: "Phone must be 7–15 digits, optionally prefixed with +",
  })
  .optional();

const profileSchema = z.object({
  full_name: z.string().min(1, "Name is required"),
  phone: phoneSchema,
  preferred_currency: z.string().min(1),
});

type ProfileFormData = z.infer<typeof profileSchema>;

interface ProfileFormProps {
  user: UserResponse;
}

export function ProfileForm({ user }: ProfileFormProps) {
  const { data: currencies } = useSupportedCurrencies();
  const { setDisplayCurrency } = useCurrencyStore();
  const setAuth = useAuthStore((s) => s.setAuth);
  const getRefreshToken = useAuthStore((s) => s.getRefreshToken);

  const {
    register,
    handleSubmit,
    setValue,
    watch,
    formState: { errors },
  } = useForm<ProfileFormData>({
    resolver: zodResolver(profileSchema),
    defaultValues: {
      full_name: user.full_name,
      phone: user.phone ?? "",
      preferred_currency: user.preferred_currency ?? "USD",
    },
  });

  const currentCurrency = watch("preferred_currency");

  const updateProfile = useMutation({
    mutationFn: async (data: ProfileFormData) => {
      const { data: updated } = await api.patch<UserResponse>("/auth/me", {
        full_name: data.full_name,
        phone: data.phone || null,
        preferred_currency: data.preferred_currency,
      });
      return updated;
    },
    onSuccess: (updated) => {
      const refreshToken = getRefreshToken();
      const accessToken = useAuthStore.getState().accessToken;
      if (accessToken && refreshToken) {
        setAuth(accessToken, refreshToken, updated);
      }
      setDisplayCurrency(updated.preferred_currency);
      toast.success("Profile updated");
      if (updated.preferred_currency !== user.preferred_currency) {
        window.location.reload();
      }
    },
    onError: () => toast.error("Failed to update profile"),
  });

  return (
    <Card>
      <CardHeader>
        <CardTitle>Personal Information</CardTitle>
        <CardDescription>Update your profile and display preferences</CardDescription>
      </CardHeader>
      <CardContent>
        <form onSubmit={handleSubmit((d) => updateProfile.mutate(d))} className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="full_name">Full Name</Label>
            <Input id="full_name" {...register("full_name")} />
            {errors.full_name && (
              <p className="text-xs text-destructive">{errors.full_name.message}</p>
            )}
          </div>

          <div className="space-y-2">
            <Label htmlFor="email">Email</Label>
            <Input id="email" value={user.email} disabled className="bg-muted" />
          </div>

          <div className="space-y-2">
            <Label htmlFor="phone">Phone</Label>
            <Input id="phone" type="tel" inputMode="numeric" maxLength={16} {...register("phone")} placeholder="Optional" />
            {errors.phone && (
              <p className="text-xs text-destructive">{errors.phone.message}</p>
            )}
          </div>

          <div className="space-y-2">
            <Label>Display Currency</Label>
            <Select
              value={currentCurrency}
              onValueChange={(v) => setValue("preferred_currency", v)}
            >
              <SelectTrigger>
                <SelectValue placeholder="Select currency" />
              </SelectTrigger>
              <SelectContent>
                {(currencies ?? ["USD", "EUR", "GBP", "INR", "AUD", "CAD", "JPY"]).map(
                  (code) => (
                    <SelectItem key={code} value={code}>
                      {code}
                    </SelectItem>
                  )
                )}
              </SelectContent>
            </Select>
            <p className="text-xs text-muted-foreground">
              All prices will be displayed in this currency
            </p>
          </div>

          <Button type="submit" disabled={updateProfile.isPending}>
            {updateProfile.isPending ? "Saving..." : "Save Changes"}
          </Button>
        </form>
      </CardContent>
    </Card>
  );
}
