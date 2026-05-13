"use client";

import { useQuery } from "@tanstack/react-query";
import { Phone, Mail, HelpCircle } from "lucide-react";
import api from "@/lib/api";
import type { UserResponse } from "@/types/api";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

interface SupportContactCardProps {
  userId: string;
}

export function SupportContactCard({ userId }: SupportContactCardProps) {
  const { data: user } = useQuery({
    queryKey: ["user", userId],
    queryFn: async () => {
      const { data } = await api.get<UserResponse>(`/auth/user/${userId}`);
      return data;
    },
    enabled: !!userId,
  });

  if (!user) return null;

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <HelpCircle className="h-4 w-4 text-muted-foreground" />
          Support Contact
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-2 text-sm">
        <p className="font-medium">{user.full_name}</p>
        <div className="flex items-center gap-2 text-muted-foreground">
          <Mail className="h-3.5 w-3.5" />
          <span>{user.email}</span>
        </div>
        {user.phone && (
          <div className="flex items-center gap-2 text-muted-foreground">
            <Phone className="h-3.5 w-3.5" />
            <span>{user.phone}</span>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
