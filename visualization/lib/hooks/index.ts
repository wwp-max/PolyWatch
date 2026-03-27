// lib/hooks/index.ts
// React Query hooks — the sole data source for all components.

import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";

export function useMarkets() {
  return useQuery({
    queryKey: ["markets"],
    queryFn: api.getMarkets,
    staleTime: 60_000,
  });
}

export function usePriceHistory(slug: string) {
  return useQuery({
    queryKey: ["prices", slug],
    queryFn: () => api.getPriceHistory(slug),
    enabled: !!slug,
  });
}

export function useMarketStats(slug: string) {
  return useQuery({
    queryKey: ["stats", slug],
    queryFn: () => api.getMarketStats(slug),
    enabled: !!slug,
  });
}

export function useAnomalyEvents(slug: string) {
  return useQuery({
    queryKey: ["anomalies", slug],
    queryFn: () => api.getAnomalyEvents(slug),
    enabled: !!slug,
  });
}
