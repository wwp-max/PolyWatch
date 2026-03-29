# API Integration Implementation Plan

**Goal:** Replace all mock data with real backend API calls using TanStack React Query, redesigning components to match backend response formats.

**Architecture:** Three-layer data architecture: `lib/api.ts` (pure fetch functions) → `lib/hooks/index.ts` (React Query wrappers) → components. All components switch from synchronous service calls to hook-based async data fetching with automatic caching, loading, and error states.

**Tech Stack:** Next.js 16, React 19, TanStack React Query 5, TypeScript, ECharts

---

## Task 1: Create type definitions

**Files:**
- Create: `lib/types.ts`

**Step 1: Create `lib/types.ts`**

```typescript
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
```

**Step 2: Verify no TypeScript errors**

Run: `npx tsc --noEmit lib/types.ts` or just ensure it compiles with the project.

---

## Task 2: Create API fetch layer

**Files:**
- Create: `lib/api.ts`
- Create: `.env.local`

**Step 1: Create `.env.local`**

```
NEXT_PUBLIC_API_URL=http://127.0.0.1:5001
```

**Step 2: Create `lib/api.ts`**

```typescript
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
```

**Step 3: Verify backend is reachable**

Run: `curl -s http://127.0.0.1:5001/api/health`
Expected: `{"service":"polywatch-api","status":"ok"}`

---

## Task 3: Create React Query provider

**Files:**
- Create: `lib/providers.tsx`
- Modify: `app/layout.tsx`

**Step 1: Create `lib/providers.tsx`**

```typescript
// lib/providers.tsx
"use client";

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useState, type ReactNode } from "react";

export function QueryProvider({ children }: { children: ReactNode }) {
  const [queryClient] = useState(
    () =>
      new QueryClient({
        defaultOptions: {
          queries: {
            staleTime: 30_000,
            retry: 2,
            refetchOnWindowFocus: false,
          },
        },
      }),
  );

  return (
    <QueryClientProvider client={queryClient}>
      {children}
    </QueryClientProvider>
  );
}
```

**Step 2: Modify `app/layout.tsx`**

Add import and wrap children:

```typescript
import { QueryProvider } from "@/lib/providers";
```

Change the body content from:
```tsx
<ThemeProvider>{children}</ThemeProvider>
```
to:
```tsx
<QueryProvider>
  <ThemeProvider>{children}</ThemeProvider>
</QueryProvider>
```

Note: `QueryProvider` must be outside `ThemeProvider` (or at least at the same level) so all children have access to the query client.

**Step 3: Verify the app still loads**

Run: `pnpm dev`
Expected: App loads without errors at http://localhost:3000

---

## Task 4: Create React Query hooks

**Files:**
- Create: `lib/hooks/index.ts`

**Step 1: Create `lib/hooks/index.ts`**

```typescript
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
```

---

## Task 5: Modify `app/page.tsx` — use `useMarkets` hook

**Files:**
- Modify: `app/page.tsx`

**Step 1: Rewrite page to use hook**

Replace entire file. Key changes:
- Import `useMarkets` from `@/lib/hooks`
- Remove `import { getMarkets } from "@/lib/services"`
- Call `useMarkets()` to get `{ data: markets, isLoading, isError }`
- Handle loading/error states
- Default `selectedSlug` to first market slug when data loads (use `useEffect`)

```typescript
"use client";

import { useState, useEffect } from "react";
import { Separator } from "@/components/ui/separator";
import StatsBar from "@/components/StatsBar";
import MarketSidebar from "@/components/MarketSidebar";
import PriceChart from "@/components/PriceChart";
import AnomalyFeed from "@/components/AnomalyFeed";
import ThemeToggle from "@/components/ThemeToggle";
import { useMarkets } from "@/lib/hooks";

export default function Home() {
  const { data: markets, isLoading, isError } = useMarkets();
  const [selectedSlug, setSelectedSlug] = useState("");
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);

  // Set default selection when markets load
  useEffect(() => {
    if (markets && markets.length > 0 && !selectedSlug) {
      setSelectedSlug(markets[0].slug);
    }
  }, [markets, selectedSlug]);

  if (isLoading) {
    return (
      <div className="flex h-screen items-center justify-center bg-background">
        <p className="font-mono text-sm text-muted-foreground">Loading markets...</p>
      </div>
    );
  }

  if (isError || !markets) {
    return (
      <div className="flex h-screen items-center justify-center bg-background">
        <p className="font-mono text-sm text-red-500">
          Failed to load markets. Is the backend running?
        </p>
      </div>
    );
  }

  const selectedMarket = markets.find((m) => m.slug === selectedSlug);

  return (
    /* ... keep existing JSX layout unchanged ... */
  );
}
```

Keep the entire JSX return block from the original file — only the data fetching and state initialization changes.

**Step 2: Verify page loads with real market data**

Run: `pnpm dev` and check http://localhost:3000
Expected: Sidebar shows 6 markets from backend (not 3 from mock)

---

## Task 6: Modify `components/MarketSidebar.tsx`

**Files:**
- Modify: `components/MarketSidebar.tsx`

**Step 1: Switch to hook**

Replace:
```typescript
import { getMarkets } from "@/lib/services";
```
with:
```typescript
import { useMarkets } from "@/lib/hooks";
```

Replace:
```typescript
const markets = getMarkets();
```
with:
```typescript
const { data: markets = [] } = useMarkets();
```

The rest of the component stays the same — it already handles the `markets` array correctly.

**Step 2: Verify sidebar displays all 6 real markets**

---

## Task 7: Modify `components/StatsBar.tsx` — redesign for backend fields

**Files:**
- Modify: `components/StatsBar.tsx`

**Step 1: Rewrite StatsBar**

Replace the entire component. Key changes:
- Import `useMarketStats` from `@/lib/hooks`
- Display backend fields: `avgPrice`, `rowCount`, `firstTime`, `lastTime`
- Handle loading/error states

```typescript
"use client";

import { Card } from "@/components/ui/card";
import { useMarketStats } from "@/lib/hooks";
import { Activity, BarChart3, Clock, CalendarDays } from "lucide-react";

interface StatsBarProps {
  slug: string;
}

export default function StatsBar({ slug }: StatsBarProps) {
  const { data: stats, isLoading } = useMarketStats(slug);

  if (isLoading || !stats) {
    return (
      <div className="grid grid-cols-2 gap-3 xl:grid-cols-4">
        {[...Array(4)].map((_, i) => (
          <Card key={i} className="flex h-24 items-center justify-center border-border bg-card">
            <p className="text-sm text-muted-foreground">Loading...</p>
          </Card>
        ))}
      </div>
    );
  }

  const formatDate = (iso: string | null) => {
    if (!iso) return "N/A";
    return new Date(iso).toLocaleDateString("en-US", {
      month: "short",
      day: "numeric",
      year: "numeric",
    });
  };

  const cards = [
    {
      label: "Average Price",
      value: stats.avgPrice != null ? `${(stats.avgPrice * 100).toFixed(1)}%` : "N/A",
      icon: BarChart3,
      color: "text-info",
    },
    {
      label: "Data Points",
      value: stats.rowCount.toLocaleString(),
      icon: Activity,
      color: "text-primary",
    },
    {
      label: "First Record",
      value: formatDate(stats.firstTime),
      icon: CalendarDays,
      color: "text-positive",
    },
    {
      label: "Last Record",
      value: formatDate(stats.lastTime),
      icon: Clock,
      color: "text-warning",
    },
  ];

  return (
    <div className="grid grid-cols-2 gap-3 xl:grid-cols-4">
      {cards.map((card) => (
        <Card
          key={card.label}
          className="flex flex-col items-center justify-center border-border bg-card px-3 py-3 text-center"
        >
          <div className={`${card.color} mb-1.5`}>
            <card.icon className="h-5 w-5" />
          </div>
          <p className="text-sm text-muted-foreground">{card.label}</p>
          <p className="font-mono text-lg font-semibold text-foreground">{card.value}</p>
        </Card>
      ))}
    </div>
  );
}
```

---

## Task 8: Modify `components/PriceChart.tsx`

**Files:**
- Modify: `components/PriceChart.tsx`

**Step 1: Switch to hooks**

Replace:
```typescript
import { getPriceHistory, getAnomalyEvents } from "@/lib/services";
```
with:
```typescript
import { usePriceHistory, useAnomalyEvents } from "@/lib/hooks";
```

Replace:
```typescript
const prices = getPriceHistory(slug);
const anomalies = getAnomalyEvents(slug);
```
with:
```typescript
const { data: prices = [] } = usePriceHistory(slug);
const { data: anomalies = [] } = useAnomalyEvents(slug);
```

**Step 2: Update anomaly markPoint tooltip**

The `detail` field is now an object. Update the markPoint name construction (around line 58):

From:
```typescript
name: `${a.eventType} | ${a.severity}\n${a.detail}`,
```
To:
```typescript
name: `${a.eventType} | ${a.severity}\n${Object.entries(a.detail).map(([k, v]) => `${k}: ${v}`).join("\n")}`,
```

**Step 3: Verify chart renders with real price data and anomaly markers**

---

## Task 9: Modify `components/AnomalyFeed.tsx`

**Files:**
- Modify: `components/AnomalyFeed.tsx`

**Step 1: Switch to hook**

Replace:
```typescript
import { getAnomalyEvents } from "@/lib/services";
```
with:
```typescript
import { useAnomalyEvents } from "@/lib/hooks";
```

Replace:
```typescript
const anomalies = getAnomalyEvents(slug);
```
with:
```typescript
const { data: anomalies = [], isLoading } = useAnomalyEvents(slug);
```

Add loading state handling before the empty check.

**Step 2: Extend `eventTypeConfig`**

Replace the existing config with:

```typescript
import { AlertTriangle, Wallet, TrendingUp, BarChart3 } from "lucide-react";

const eventTypeConfig: Record<string, { label: string; icon: typeof AlertTriangle }> = {
  zscore_spike: {
    label: "Z-Score Spike",
    icon: AlertTriangle,
  },
  whale_trade: {
    label: "Whale Trade",
    icon: Wallet,
  },
  whale_directional_bias: {
    label: "Directional Bias",
    icon: TrendingUp,
  },
  benford_violation: {
    label: "Benford Violation",
    icon: BarChart3,
  },
};
```

**Step 3: Update detail rendering**

Replace the detail paragraph (line ~97):

From:
```tsx
<p className="mt-1.5 text-sm leading-relaxed text-muted-foreground">
  {anomaly.detail}
</p>
```
To:
```tsx
<div className="mt-1.5 flex flex-wrap gap-x-4 gap-y-1">
  {Object.entries(anomaly.detail)
    .filter(([k]) => k !== "market_slug")
    .map(([key, value]) => (
      <span key={key} className="text-xs text-muted-foreground">
        <span className="font-medium text-foreground">{key}:</span>{" "}
        {typeof value === "number" ? (Number.isInteger(value) ? value : value.toFixed(4)) : String(value)}
      </span>
    ))}
</div>
```

**Step 4: Handle typeConfig lookup safely**

Since eventType comes from backend, add fallback:

```typescript
const typeConf = eventTypeConfig[anomaly.eventType] ?? {
  label: anomaly.eventType,
  icon: AlertTriangle,
};
```

**Step 5: Verify anomaly feed shows real events with structured detail**

---

## Task 10: Clean up old service layer

**Files:**
- Modify: `lib/services/index.ts`

**Step 1: Empty the service file**

Replace contents with:

```typescript
// This file is deprecated. All data is now fetched via lib/hooks/.
// Kept to avoid breaking any lingering imports during transition.
```

Or delete the file entirely if no import references remain.

**Step 2: Verify no remaining imports of `@/lib/services`**

Run: `grep -r "from.*@/lib/services" --include="*.ts" --include="*.tsx" app/ components/ lib/`
Expected: No results.

---

## Task 11: Full integration verification

**Step 1: Run `pnpm build`**

Expected: Build completes with no TypeScript or build errors.

**Step 2: Run `pnpm dev` and test**

Manual verification checklist:
- [ ] Sidebar shows all 6 real markets from backend
- [ ] Clicking a market updates StatsBar, PriceChart, AnomalyFeed
- [ ] StatsBar shows avgPrice, rowCount, firstTime, lastTime
- [ ] PriceChart shows real price history with anomaly markers
- [ ] AnomalyFeed shows real events with structured detail (key-value pairs)
- [ ] Theme toggle still works
- [ ] No console errors

**Step 3: Commit**

```bash
git add -A
git commit -m "feat: replace mock data with real backend API integration via React Query"
```
