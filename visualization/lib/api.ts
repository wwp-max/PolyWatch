// lib/api.ts
// Pure fetch functions — no React dependency.

import type { Market, PricePoint, AnomalyEvent, MarketStats } from "@/lib/types";

const BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:5001";

async function fetchJson<T>(path: string): Promise<T> {
  const res = await fetch(`${BASE_URL}${path}`);
  if (!res.ok) {
    throw new Error(`API error ${res.status}: ${path}`);
  }
  return res.json() as Promise<T>;
}

export const api = {
  getMarkets: () =>
    fetchJson<Market[]>("/api/markets"),

  getPriceHistory: (slug: string) =>
    fetchJson<PricePoint[]>(`/api/markets/${encodeURIComponent(slug)}/prices`),

  getMarketStats: (slug: string) =>
    fetchJson<MarketStats>(`/api/markets/${encodeURIComponent(slug)}/stats`),

  getAnomalyEvents: (slug?: string) => {
    const params = slug ? `?slug=${encodeURIComponent(slug)}` : "";
    return fetchJson<AnomalyEvent[]>(`/api/anomalies${params}`);
  },
};
