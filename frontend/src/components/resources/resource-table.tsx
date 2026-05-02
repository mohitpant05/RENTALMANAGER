"use client";

import { MoreHorizontal, Pencil, Trash2, ExternalLink } from "lucide-react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import api from "@/lib/api";
import type { ResourceResponse } from "@/types/api";
import { toast } from "sonner";

const STATUS_VARIANT: Record<
  string,
  "muted" | "success" | "warning" | "destructive"
> = {
  draft: "muted",
  active: "success",
  inactive: "warning",
  archived: "destructive",
};

interface ResourceTableProps {
  resources: ResourceResponse[];
  typeId: string;
  typeSlug: string;
  onEdit: (resource: ResourceResponse) => void;
}

export function ResourceTable({
  resources,
  typeId,
  typeSlug,
  onEdit,
}: ResourceTableProps) {
  const queryClient = useQueryClient();

  const deleteMutation = useMutation({
    mutationFn: async (id: string) => {
      await api.delete(`/resources/${id}`);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["resources", typeId] });
      toast.success("Resource deleted");
    },
    onError: () => {
      toast.error("Failed to delete resource");
    },
  });

  if (resources.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center rounded-lg border border-dashed py-16">
        <p className="text-muted-foreground">No resources yet</p>
        <p className="mt-1 text-sm text-muted-foreground">
          Add your first resource to get started
        </p>
      </div>
    );
  }

  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead>Name</TableHead>
          <TableHead>Status</TableHead>
          <TableHead>Price</TableHead>
          <TableHead>Rating</TableHead>
          <TableHead>Created</TableHead>
          <TableHead className="w-[50px]" />
        </TableRow>
      </TableHeader>
      <TableBody>
        {resources.map((r) => (
          <TableRow key={r.id}>
            <TableCell className="font-medium">
              <Link
                href={`/resources/${typeSlug}/${r.id}`}
                className="hover:underline"
              >
                {r.name}
              </Link>
            </TableCell>
            <TableCell>
              <Badge variant={STATUS_VARIANT[r.status] ?? "muted"}>
                {r.status}
              </Badge>
            </TableCell>
            <TableCell>
              {r.base_price.toFixed(2)} {r.currency}
            </TableCell>
            <TableCell>
              {r.rating_count > 0
                ? `${r.rating_avg.toFixed(1)} (${r.rating_count})`
                : "—"}
            </TableCell>
            <TableCell className="text-muted-foreground">
              {new Date(r.created_at).toLocaleDateString()}
            </TableCell>
          <TableCell>
            <DropdownMenu>
              <DropdownMenuTrigger
                render={<Button variant="ghost" size="icon" className="h-8 w-8" />}
              >
                <MoreHorizontal className="h-4 w-4" />
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end">
                <DropdownMenuItem
                  render={
                    <Link href={`/resources/${typeSlug}/${r.id}`}>
                      <ExternalLink className="mr-2 h-4 w-4" />
                      View
                    </Link>
                  }
                />
                <DropdownMenuItem onClick={() => onEdit(r)}>
                  <Pencil className="mr-2 h-4 w-4" />
                  Edit
                </DropdownMenuItem>
                <DropdownMenuItem
                  onClick={() => deleteMutation.mutate(r.id)}
                  className="text-destructive focus:text-destructive"
                >
                  <Trash2 className="mr-2 h-4 w-4" />
                  Delete
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          </TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  );
}
