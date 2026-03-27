// ============================================================
// Mock data for PolyWatch frontend development.
// This file is ONLY imported by lib/services/index.ts.
// When FastAPI is ready, services/index.ts will switch to fetch().
// ============================================================

// ----- Types (frontend-only rendering types) -----

export interface Market {
  slug: string;
  question: string;
  active: boolean;
  /** Most recent price (0-1) */
  lastPrice: number;
  /** Price 24h ago for calculating change */
  prevPrice: number;
}

export interface PricePoint {
  time: string; // ISO 8601
  price: number; // 0-1
}

export interface AnomalyEvent {
  id: number;
  marketSlug: string;
  detectedAt: string; // ISO 8601
  eventType: "zscore_spike" | "whale_alert" | "volume_surge";
  severity: "high" | "medium" | "low";
  detail: string;
}

// ----- Helper: generate price series with random walk -----

function generatePriceSeries(
  startDate: Date,
  endDate: Date,
  startPrice: number,
  endPrice: number,
  volatility: number,
  intervalMinutes: number = 60,
): PricePoint[] {
  const points: PricePoint[] = [];
  const totalMs = endDate.getTime() - startDate.getTime();
  const stepMs = intervalMinutes * 60 * 1000;
  const steps = Math.floor(totalMs / stepMs);

  // Linear drift per step + random walk
  const drift = (endPrice - startPrice) / steps;
  let price = startPrice;

  // Seed-like deterministic "random" using simple LCG for reproducibility
  let seed = Math.abs(startPrice * 10000 + endPrice * 10000) | 0;
  function pseudoRandom(): number {
    seed = (seed * 1664525 + 1013904223) & 0xffffffff;
    return (seed >>> 0) / 0xffffffff;
  }

  for (let i = 0; i <= steps; i++) {
    const t = new Date(startDate.getTime() + i * stepMs);
    const noise = (pseudoRandom() - 0.5) * 2 * volatility;
    price = price + drift + noise;
    // Clamp to 0-1
    price = Math.max(0.01, Math.min(0.99, price));
    points.push({
      time: t.toISOString(),
      price: Math.round(price * 10000) / 10000,
    });
  }

  // Ensure last point matches target roughly
  if (points.length > 0) {
    points[points.length - 1].price = Math.round(endPrice * 10000) / 10000;
  }

  return points;
}

// ----- Markets -----

export const mockMarkets: Market[] = [
  {
    slug: "presidential-election-winner-2024",
    question: "Will Donald Trump win the 2024 US Presidential Election?",
    active: false,
    lastPrice: 0.95,
    prevPrice: 0.92,
  },
  {
    slug: "what-will-happen-before-gta-vi",
    question: "Russia-Ukraine Ceasefire before GTA VI?",
    active: true,
    lastPrice: 0.58,
    prevPrice: 0.61,
  },
  {
    slug: "will-trump-acquire-greenland-before-2027",
    question: "Will Trump acquire Greenland before 2027?",
    active: true,
    lastPrice: 0.11,
    prevPrice: 0.1,
  },
];

// ----- Price History -----

// Election market: Jan 5 2024 → Nov 6 2024, ~0.54 → ~0.95, 200 points for demo
const electionPrices = generatePriceSeries(
  new Date("2024-01-05T00:00:00Z"),
  new Date("2024-11-06T00:00:00Z"),
  0.54,
  0.95,
  0.015,
  // ~200 points: interval = total hours / 200 ≈ 37 hours
  37 * 60,
);

// GTA VI market: Feb 4 2026 → Mar 8 2026, fluctuates ~0.58
const gtaPrices = generatePriceSeries(
  new Date("2026-02-04T00:00:00Z"),
  new Date("2026-03-08T00:00:00Z"),
  0.56,
  0.58,
  0.02,
  60, // hourly
);

// Greenland market: Feb 4 2026 → Mar 8 2026, fluctuates ~0.11
const greenlandPrices = generatePriceSeries(
  new Date("2026-02-04T00:00:00Z"),
  new Date("2026-03-08T00:00:00Z"),
  0.09,
  0.11,
  0.01,
  60,
);

export const mockPriceHistory: Record<string, PricePoint[]> = {
  "presidential-election-winner-2024": electionPrices,
  "what-will-happen-before-gta-vi": gtaPrices,
  "will-trump-acquire-greenland-before-2027": greenlandPrices,
};

// ----- Anomaly Events -----

export const mockAnomalyEvents: AnomalyEvent[] = [
  {
    id: 1,
    marketSlug: "presidential-election-winner-2024",
    detectedAt: "2024-07-14T03:15:00Z",
    eventType: "zscore_spike",
    severity: "high",
    detail:
      "Z-score reached 4.2 after Trump assassination attempt. Price surged from 0.58 to 0.68 within 2 hours.",
  },
  {
    id: 2,
    marketSlug: "presidential-election-winner-2024",
    detectedAt: "2024-09-11T02:30:00Z",
    eventType: "volume_surge",
    severity: "medium",
    detail:
      "Trading volume 3.5x above average during presidential debate. Price moved from 0.52 to 0.57.",
  },
  {
    id: 3,
    marketSlug: "presidential-election-winner-2024",
    detectedAt: "2024-10-28T18:00:00Z",
    eventType: "whale_alert",
    severity: "high",
    detail:
      "Single wallet placed $2.1M YES position. Price jumped from 0.62 to 0.67 in 30 minutes.",
  },
  {
    id: 4,
    marketSlug: "what-will-happen-before-gta-vi",
    detectedAt: "2026-02-24T10:00:00Z",
    eventType: "zscore_spike",
    severity: "high",
    detail:
      "Z-score 3.8 detected. Ceasefire rumors pushed price from 0.52 to 0.64 in 4 hours.",
  },
  {
    id: 5,
    marketSlug: "what-will-happen-before-gta-vi",
    detectedAt: "2026-03-02T14:30:00Z",
    eventType: "volume_surge",
    severity: "medium",
    detail:
      "Volume spike 2.8x normal after UN Security Council session. Price fluctuated between 0.55 and 0.62.",
  },
  {
    id: 6,
    marketSlug: "will-trump-acquire-greenland-before-2027",
    detectedAt: "2026-02-15T09:00:00Z",
    eventType: "whale_alert",
    severity: "low",
    detail:
      "Large YES position opened ($180K). Price moved from 0.08 to 0.12.",
  },
  {
    id: 7,
    marketSlug: "will-trump-acquire-greenland-before-2027",
    detectedAt: "2026-03-05T16:45:00Z",
    eventType: "zscore_spike",
    severity: "medium",
    detail:
      "Z-score 2.9 after Danish PM comments. Price spiked from 0.10 to 0.15, reverted to 0.11.",
  },
];
