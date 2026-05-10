"use client";

import { useRouter } from "next/navigation";
import { useAuthStore } from "@/lib/auth-store";
import { useMyReviews } from "@/hooks/use-reviews";
import { ProfileForm } from "@/components/public/profile-form";
import { StarRating } from "@/components/reviews/star-rating";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Lock } from "lucide-react";

export default function ProfilePage() {
  const router = useRouter();
  const user = useAuthStore((s) => s.user);
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated);
  const isLoading = useAuthStore((s) => s.isLoading);

  if (!isLoading && !isAuthenticated) {
    router.push("/login?returnUrl=/profile");
    return null;
  }

  const { data: reviews, isLoading: reviewsLoading } = useMyReviews({ limit: 20 });

  if (isLoading) {
    return (
      <div className="flex min-h-[60vh] items-center justify-center">
        <div className="h-8 w-8 animate-spin rounded-full border-2 border-primary border-t-transparent" />
      </div>
    );
  }

  if (!user) return null;

  return (
    <div className="mx-auto max-w-2xl px-4 py-6 space-y-6">
      <h1 className="text-2xl font-bold">Profile</h1>

      <ProfileForm user={user} />

      <Card>
        <CardHeader>
          <CardTitle>My Reviews</CardTitle>
          <CardDescription>Reviews you have written</CardDescription>
        </CardHeader>
        <CardContent>
          {reviewsLoading && (
            <div className="space-y-3">
              {[1, 2].map((i) => (
                <div key={i} className="h-16 animate-pulse rounded bg-muted" />
              ))}
            </div>
          )}

          {reviews && reviews.length === 0 && (
            <p className="text-sm text-muted-foreground">
              You haven't written any reviews yet.
            </p>
          )}

          {reviews && reviews.length > 0 && (
            <div className="space-y-4">
              {reviews.map((review) => (
                <div key={review.id} className="space-y-1 border-b pb-3 last:border-0">
                  <div className="flex items-center gap-3">
                    <StarRating rating={review.rating} size="sm" />
                    <span className="text-xs text-muted-foreground">
                      {new Date(review.created_at).toLocaleDateString()}
                    </span>
                  </div>
                  {review.comment && (
                    <p className="text-sm text-muted-foreground line-clamp-2">
                      {review.comment}
                    </p>
                  )}
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Lock className="h-4 w-4" />
            Change Password
          </CardTitle>
          <CardDescription>Coming soon</CardDescription>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground">
            Password changes will be available in a future update.
          </p>
        </CardContent>
      </Card>
    </div>
  );
}
