import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import api from "@/lib/api";
import type { AttachmentResponse } from "@/types/api";

const ALLOWED_TYPES = ["image/jpeg", "image/png", "image/webp", "image/gif"];
const MAX_SIZE = 10 * 1024 * 1024; // 10MB

export function useAttachments(entityType: string, entityId: string) {
  return useQuery({
    queryKey: ["attachments", entityType, entityId],
    queryFn: async () => {
      const { data } = await api.get<AttachmentResponse[]>(
        `/storage/attachments?entity_type=${entityType}&entity_id=${entityId}`
      );
      return data;
    },
    enabled: !!entityId,
  });
}

/**
 * Upload a file to MinIO via the backend proxy.
 *
 * Flow: browser → Next.js rewrite (/api/:path* → backend:8000/:path*) → backend → MinIO (internal)
 *
 * The relative path ("/api" baseURL) works in all environments:
 * - Dev:  Next.js rewrites /api/* → http://localhost:8000/api/*
 * - Prod: Ingress routes /api/* → backend Service:8000
 *
 * No presigned URLs or direct S3 access from the browser.
 */
export function useUpload(entityType: string, entityId: string) {
  const queryClient = useQueryClient();
  const [isUploading, setIsUploading] = useState(false);

  async function upload(file: File): Promise<AttachmentResponse | null> {
    if (!ALLOWED_TYPES.includes(file.type)) {
      throw new Error("File type not supported. Use JPG, PNG, WebP, or GIF.");
    }
    if (file.size > MAX_SIZE) {
      throw new Error("File too large. Maximum 10MB.");
    }

    setIsUploading(true);
    try {
      // Multipart POST to the backend-proxied upload endpoint.
      // Backend validates type/size, uploads to MinIO internally,
      // creates the Attachment record, and returns it with a presigned download URL.
      const form = new FormData();
      form.append("file", file);
      form.append("entity_type", entityType);
      form.append("entity_id", entityId);

      const { data } = await api.post<AttachmentResponse>("/storage/upload", form);

      queryClient.invalidateQueries({ queryKey: ["attachments", entityType, entityId] });
      return data;
    } finally {
      setIsUploading(false);
    }
  }

  const deleteMutation = useMutation({
    mutationFn: async (attachmentId: string) => {
      await api.delete(`/storage/attachments/${attachmentId}`);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["attachments", entityType, entityId] });
    },
  });

  return { upload, isUploading, deleteAttachment: deleteMutation.mutate, isDeleting: deleteMutation.isPending };
}
