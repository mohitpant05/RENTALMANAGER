import { useQuery, keepPreviousData } from "@tanstack/react-query";
import api from "@/lib/api";
import type { SearchRequest, SearchResponse } from "@/types/api";

export function useSearch(params: SearchRequest, enabled = true) {
  return useQuery({
    queryKey: ["search", params],
    queryFn: async () => {
      const { data } = await api.post<SearchResponse>("/search", params);
      return data;
    },
    enabled,
    placeholderData: keepPreviousData,
  });
}
