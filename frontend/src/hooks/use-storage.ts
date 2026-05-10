import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import axios from "axios";
import api from "@/lib/api";
import type { AttachmentResponse, UploadUrlRequest, UploadUrlResponse } from "@/types/api";

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
      const { data: urlData } = await api.post<UploadUrlResponse>("/storage/upload-url", {
        filename: file.name,
        content_type: file.type,
        entity_type: entityType,
        entity_id: entityId,
      } as UploadUrlRequest);

      await axios.put(urlData.upload_url, file, {
        headers: { "Content-Type": file.type },
      });

      const { data: attachment } = await api.post<AttachmentResponse>("/storage/confirm", {
        attachment_id: urlData.attachment_id,
      });

      queryClient.invalidateQueries({ queryKey: ["attachments", entityType, entityId] });
      return attachment;
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
