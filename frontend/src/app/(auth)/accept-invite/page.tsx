"use client";

import { useState, useEffect } from "react";
import { useSearchParams } from "next/navigation";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { Eye, EyeOff } from "lucide-react";
import { useAuth } from "@/hooks/use-auth";
import api from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { toast } from "sonner";
import type { VerifyInviteResponse } from "@/types/api";

const acceptSchema = z
  .object({
    password: z.string().min(8, "Password must be at least 8 characters"),
    confirmPassword: z.string(),
  })
  .refine((data) => data.password === data.confirmPassword, {
    message: "Passwords do not match",
    path: ["confirmPassword"],
  });

type AcceptForm = z.infer<typeof acceptSchema>;

export default function AcceptInvitePage() {
  const searchParams = useSearchParams();
  const token = searchParams.get("token");
  const { acceptInvite } = useAuth();

  const [verifying, setVerifying] = useState(true);
  const [inviteData, setInviteData] = useState<VerifyInviteResponse | null>(
    null,
  );
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [showPassword, setShowPassword] = useState(false);

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<AcceptForm>({
    resolver: zodResolver(acceptSchema),
  });

  useEffect(() => {
    if (!token) {
      setVerifying(false);
      return;
    }
    api
      .get<VerifyInviteResponse>(`/auth/verify-invite?token=${token}`)
      .then((res) => setInviteData(res.data))
      .catch(() => setInviteData({ valid: false }))
      .finally(() => setVerifying(false));
  }, [token]);

  async function onSubmit(data: AcceptForm) {
    if (!token) return;
    setIsSubmitting(true);
    try {
      await acceptInvite({ token, password: data.password });
    } catch (error: unknown) {
      const axiosError = error as {
        response?: { data?: { detail?: string } };
      };
      toast.error(
        axiosError.response?.data?.detail || "Failed to accept invite",
      );
    } finally {
      setIsSubmitting(false);
    }
  }

  if (verifying) {
    return (
      <Card className="w-full max-w-md">
        <CardContent className="flex items-center justify-center py-12">
          <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary border-t-transparent" />
        </CardContent>
      </Card>
    );
  }

  if (!token || !inviteData?.valid) {
    return (
      <Card className="w-full max-w-md">
        <CardHeader className="text-center">
          <CardTitle className="text-2xl">Invalid Invite</CardTitle>
          <CardDescription>
            This invite link is invalid or has expired. Please contact your
            administrator for a new invite.
          </CardDescription>
        </CardHeader>
      </Card>
    );
  }

  return (
    <Card className="w-full max-w-md">
      <CardHeader className="text-center">
        <CardTitle className="text-2xl">Set your password</CardTitle>
        <CardDescription>
          Complete your account setup to get started
        </CardDescription>
      </CardHeader>
      <CardContent>
        <div className="mb-6 space-y-2">
          <div>
            <Label className="text-muted-foreground text-xs">Name</Label>
            <p className="font-medium">{inviteData.full_name}</p>
          </div>
          <div>
            <Label className="text-muted-foreground text-xs">Email</Label>
            <p className="font-medium">{inviteData.email}</p>
          </div>
        </div>
        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="password">Password</Label>
            <div className="relative">
              <Input
                id="password"
                type={showPassword ? "text" : "password"}
                className="pr-10"
                {...register("password")}
              />
              <button
                type="button"
                onClick={() => setShowPassword(!showPassword)}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
                tabIndex={-1}
              >
                {showPassword ? (
                  <EyeOff className="h-4 w-4" />
                ) : (
                  <Eye className="h-4 w-4" />
                )}
              </button>
            </div>
            {errors.password && (
              <p className="text-sm text-destructive">
                {errors.password.message}
              </p>
            )}
          </div>
          <div className="space-y-2">
            <Label htmlFor="confirmPassword">Confirm Password</Label>
            <Input
              id="confirmPassword"
              type={showPassword ? "text" : "password"}
              {...register("confirmPassword")}
            />
            {errors.confirmPassword && (
              <p className="text-sm text-destructive">
                {errors.confirmPassword.message}
              </p>
            )}
          </div>
          <Button type="submit" className="w-full" disabled={isSubmitting}>
            {isSubmitting ? "Activating account..." : "Activate account"}
          </Button>
        </form>
      </CardContent>
    </Card>
  );
}
