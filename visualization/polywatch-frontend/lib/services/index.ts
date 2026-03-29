// ============================================================
// Service Layer — the ONLY data source for all components.
//
// Currently returns mock data from lib/mock/data.ts.
// When FastAPI is ready, replace the implementations below
// with fetch() calls. No component code needs to change.
// ============================================================

import {
  mockMarkets,
  mockPriceHistory,
  mockAnomalyEvents,
  type Market,
  type PricePoint,
  type AnomalyEvent,
} from "@/lib/mock/data";

/**
 * Get all monitored markets.
 */
export function getMarkets(): Market[] {
  return mockMarkets;
}

/**
 * Get price history for a specific market by slug.
 * Returns an empty array if the market slug is not found.
 */
export function getPriceHistory(slug: string): PricePoint[] {
  return mockPriceHistory[slug] ?? [];
}

/**
 * Get anomaly events for a specific market by slug.
 * Returns events sorted newest-first.
 */
export function getAnomalyEvents(slug: string): AnomalyEvent[] {
  return mockAnomalyEvents
    .filter((e) => e.marketSlug === slug)
    .sort(
      (a, b) =>
        new Date(b.detectedAt).getTime() - new Date(a.detectedAt).getTime(),
    );
}

/**
 * Get all anomaly events across all markets.
 * Returns events sorted newest-first.
 */
export function getAllAnomalyEvents(): AnomalyEvent[] {
  return [...mockAnomalyEvents].sort(
    (a, b) =>
      new Date(b.detectedAt).getTime() - new Date(a.detectedAt).getTime(),
  );
}

/**
 * Per-market statistics for StatsBar.
 */
export interface MarketStats {
  dataPoints: number;
  anomalyCount: number;
  maxSwing: number;
  currentPrice: number;
  priceChange: number;
  active: boolean;
}

/**
 * Get computed statistics for a single market.
 */
export function getMarketStats(slug: string): MarketStats {
  const market = mockMarkets.find((m) => m.slug === slug);
  const prices = getPriceHistory(slug);
  const anomalies = getAnomalyEvents(slug);

  // Max single-step price swing
  let maxSwing = 0;
  for (let i = 1; i < prices.length; i++) {
    const swing = Math.abs(prices[i].price - prices[i - 1].price);
    if (swing > maxSwing) maxSwing = swing;
  }

  const priceChange = market ? market.lastPrice - market.prevPrice : 0;

  return {
    dataPoints: prices.length,
    anomalyCount: anomalies.length,
    maxSwing,
    currentPrice: market?.lastPrice ?? 0,
    priceChange,
    active: market?.active ?? false,
  };
}

// Re-export types for component use
export type { Market, PricePoint, AnomalyEvent };
