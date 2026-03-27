// lib/types.ts
// Type definitions aligned to backend API responses.

export interface Market {
  slug: string;
  question: string;
  active: boolean;
  lastPrice: number;
  prevPrice: number;
}

export interface PricePoint {
  time: string;   // ISO 8601
  price: number;
}

export interface AnomalyEvent {
  id: number;
  marketSlug: string;
  detectedAt: string;   // ISO 8601
  eventType: "zscore_spike" | "whale_trade" | "whale_directional_bias" | "benford_violation";
  severity: "high" | "medium" | "low";
  detail: Record<string, unknown>;
}

export interface MarketStats {
  slug: string;
  question: string;
  rowCount: number;
  firstTime: string | null;
  lastTime: string | null;
  avgPrice: number | null;
}
