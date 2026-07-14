"use client";

import { useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { useMutation } from "@tanstack/react-query";
import { Eye, EyeOff, Loader2, Lock, Mail, User as UserIcon } from "lucide-react";
import api from "@/lib/api";
import { useAuthStore } from "@/lib/auth-store";
import type { UserResponse } from "@/types/api";
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

const profileSchema = z.object({
  full_name: z.string().min(1, "Name is required"),
  phone: z
    .string()
    .refine((v) => !v || /^\+?\d{7,15}$/.test(v), {
      message: "Phone must be 7-15 digits, optionally prefixed with +",
    })
    .optional(),
});

type ProfileFormData = z.infer<typeof profileSchema>;

const passwordSchema = z
  .object({
    current_password: z.string().min(1, "Required"),
    new_password: z.string().min(8, "Must be at least 8 characters"),
    confirm_password: z.string().min(1, "Required"),
  })
  .refine((d) => d.new_password === d.confirm_password, {
    message: "Passwords don't match",
    path: ["confirm_password"],
  });

type PasswordFormData = z.infer<typeof passwordSchema>;

const emailRequestSchema = z.object({
  new_email: z.string().email("Invalid email"),
  password: z.string().min(1, "Required"),
});

type EmailRequestData = z.infer<typeof emailRequestSchema>;

export default function AdminProfilePage() {
  const user = useAuthStore((s) => s.user);

  if (!user) return null;

  return (
    <div className="mx-auto max-w-2xl space-y-6">
      <h1 className="text-2xl font-bold tracking-tight">Profile</h1>
      <ProfileSection user={user} />
      <EmailChangeSection user={user} />
      <PasswordSection />
    </div>
  );
}

function ProfileSection({ user }: { user: UserResponse }) {
  const setAuth = useAuthStore((s) => s.setAuth);
  const getRefreshToken = useAuthStore((s) => s.getRefreshToken);

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<ProfileFormData>({
    resolver: zodResolver(profileSchema),
    defaultValues: {
      full_name: user.full_name,
      phone: user.phone ?? "",
    },
  });

  const mutation = useMutation({
    mutationFn: async (data: ProfileFormData) => {
      const { data: updated } = await api.patch<UserResponse>("/auth/me", {
        full_name: data.full_name,
        phone: data.phone || null,
      });
      return updated;
    },
    onSuccess: (updated) => {
      const refreshToken = getRefreshToken();
      const accessToken = useAuthStore.getState().accessToken;
      if (accessToken && refreshToken) {
        setAuth(accessToken, refreshToken, updated);
      }
      toast.success("Profile updated");
    },
    onError: () => toast.error("Failed to update profile"),
  });

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <UserIcon className="h-4 w-4" />
          Personal Information
        </CardTitle>
        <CardDescription>Update your name and contact details</CardDescription>
      </CardHeader>
      <CardContent>
        <form
          onSubmit={handleSubmit((d) => mutation.mutate(d))}
          className="space-y-4"
        >
          <div className="space-y-2">
            <Label htmlFor="full_name">Full Name</Label>
            <Input id="full_name" {...register("full_name")} />
            {errors.full_name && (
              <p className="text-xs text-destructive">
                {errors.full_name.message}
              </p>
            )}
          </div>
          <div className="space-y-2">
            <Label htmlFor="phone">Phone</Label>
            <Input
              id="phone"
              type="tel"
              inputMode="numeric"
              maxLength={16}
              {...register("phone")}
              placeholder="Optional"
            />
            {errors.phone && (
              <p className="text-xs text-destructive">
                {errors.phone.message}
              </p>
            )}
          </div>
          <Button type="submit" disabled={mutation.isPending}>
            {mutation.isPending ? "Saving..." : "Save Changes"}
          </Button>
        </form>
      </CardContent>
    </Card>
  );
}

function EmailChangeSection({ user }: { user: UserResponse }) {
  const [step, setStep] = useState<"request" | "verify">("request");
  const [pendingEmail, setPendingEmail] = useState("");
  const [otp, setOtp] = useState("");
  const setAuth = useAuthStore((s) => s.setAuth);
  const getRefreshToken = useAuthStore((s) => s.getRefreshToken);

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors },
  } = useForm<EmailRequestData>({
    resolver: zodResolver(emailRequestSchema),
  });

  const requestMutation = useMutation({
    mutationFn: async (data: EmailRequestData) => {
      await api.post("/auth/request-email-change", data);
      return data.new_email;
    },
    onSuccess: (newEmail) => {
      setPendingEmail(newEmail);
      setStep("verify");
      toast.success("Verification code sent to " + newEmail);
    },
    onError: (err: unknown) => {
      const detail =
        (err as { response?: { data?: { detail?: string } } })?.response?.data
          ?.detail ?? "Failed to send verification code";
      toast.error(detail);
    },
  });

  const verifyMutation = useMutation({
    mutationFn: async (code: string) => {
      const { data } = await api.post<UserResponse>(
        "/auth/verify-email-change",
        { otp: code }
      );
      return data;
    },
    onSuccess: (updated) => {
      const refreshToken = getRefreshToken();
      const accessToken = useAuthStore.getState().accessToken;
      if (accessToken && refreshToken) {
        setAuth(accessToken, refreshToken, updated);
      }
      toast.success("Email updated to " + updated.email);
      setStep("request");
      setOtp("");
      reset();
    },
    onError: (err: unknown) => {
      const detail =
        (err as { response?: { data?: { detail?: string } } })?.response?.data
          ?.detail ?? "Invalid verification code";
      toast.error(detail);
    },
  });

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Mail className="h-4 w-4" />
          Email Address
        </CardTitle>
        <CardDescription>
          Current email: <span className="font-medium">{user.email}</span>
        </CardDescription>
      </CardHeader>
      <CardContent>
        {step === "request" ? (
          <form
            onSubmit={handleSubmit((d) => requestMutation.mutate(d))}
            className="space-y-4"
          >
            <div className="space-y-2">
              <Label htmlFor="new_email">New Email</Label>
              <Input
                id="new_email"
                type="email"
                {...register("new_email")}
                placeholder="new@example.com"
              />
              {errors.new_email && (
                <p className="text-xs text-destructive">
                  {errors.new_email.message}
                </p>
              )}
            </div>
            <div className="space-y-2">
              <Label htmlFor="email_password">Current Password</Label>
              <Input
                id="email_password"
                type="password"
                {...register("password")}
                placeholder="Confirm your password"
              />
              {errors.password && (
                <p className="text-xs text-destructive">
                  {errors.password.message}
                </p>
              )}
            </div>
            <Button type="submit" disabled={requestMutation.isPending}>
              {requestMutation.isPending ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Sending...
                </>
              ) : (
                "Send Verification Code"
              )}
            </Button>
          </form>
        ) : (
          <div className="space-y-4">
            <p className="text-sm text-muted-foreground">
              Enter the 6-digit code sent to{" "}
              <span className="font-medium">{pendingEmail}</span>
            </p>
            <div className="space-y-2">
              <Label htmlFor="otp">Verification Code</Label>
              <Input
                id="otp"
                value={otp}
                onChange={(e) =>
                  setOtp(e.target.value.replace(/\D/g, "").slice(0, 6))
                }
                placeholder="000000"
                maxLength={6}
                inputMode="numeric"
                className="text-center text-lg tracking-[0.5em] font-mono"
              />
            </div>
            <div className="flex gap-2">
              <Button
                onClick={() => verifyMutation.mutate(otp)}
                disabled={otp.length !== 6 || verifyMutation.isPending}
              >
                {verifyMutation.isPending ? (
                  <>
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    Verifying...
                  </>
                ) : (
                  "Verify & Update Email"
                )}
              </Button>
              <Button
                variant="ghost"
                onClick={() => {
                  setStep("request");
                  setOtp("");
                }}
              >
                Cancel
              </Button>
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

function PasswordSection() {
  const [showCurrent, setShowCurrent] = useState(false);
  const [showNew, setShowNew] = useState(false);

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors, isSubmitting },
  } = useForm<PasswordFormData>({
    resolver: zodResolver(passwordSchema),
  });

  async function onSubmit(data: PasswordFormData) {
    try {
      await api.post("/auth/change-password", {
        current_password: data.current_password,
        new_password: data.new_password,
      });
      toast.success("Password changed");
      reset();
    } catch (error: unknown) {
      const err = error as { response?: { data?: { detail?: string } } };
      toast.error(err.response?.data?.detail || "Failed to change password");
    }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Lock className="h-4 w-4" />
          Change Password
        </CardTitle>
        <CardDescription>Update your account password</CardDescription>
      </CardHeader>
      <CardContent>
        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="current_password">Current Password</Label>
            <div className="relative">
              <Input
                id="current_password"
                type={showCurrent ? "text" : "password"}
                className="pr-10"
                {...register("current_password")}
              />
              <button
                type="button"
                onClick={() => setShowCurrent(!showCurrent)}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
                tabIndex={-1}
              >
                {showCurrent ? (
                  <EyeOff className="h-4 w-4" />
                ) : (
                  <Eye className="h-4 w-4" />
                )}
              </button>
            </div>
            {errors.current_password && (
              <p className="text-xs text-destructive">
                {errors.current_password.message}
              </p>
            )}
          </div>

          <div className="space-y-2">
            <Label htmlFor="new_password">New Password</Label>
            <div className="relative">
              <Input
                id="new_password"
                type={showNew ? "text" : "password"}
                className="pr-10"
                {...register("new_password")}
              />
              <button
                type="button"
                onClick={() => setShowNew(!showNew)}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
                tabIndex={-1}
              >
                {showNew ? (
                  <EyeOff className="h-4 w-4" />
                ) : (
                  <Eye className="h-4 w-4" />
                )}
              </button>
            </div>
            {errors.new_password && (
              <p className="text-xs text-destructive">
                {errors.new_password.message}
              </p>
            )}
          </div>

          <div className="space-y-2">
            <Label htmlFor="confirm_password">Confirm New Password</Label>
            <Input
              id="confirm_password"
              type="password"
              {...register("confirm_password")}
            />
            {errors.confirm_password && (
              <p className="text-xs text-destructive">
                {errors.confirm_password.message}
              </p>
            )}
          </div>

          <Button type="submit" disabled={isSubmitting}>
            {isSubmitting ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                Changing...
              </>
            ) : (
              "Change Password"
            )}
          </Button>
        </form>
      </CardContent>
    </Card>
  );
}
