# PolyWatch Frontend API Integration Design

> Date: 2026-03-27
> Scope: Replace mock data with real backend API calls. No backend changes.

## Context

The frontend currently uses mock data in `lib/mock/data.ts`, consumed via a synchronous service layer `lib/services/index.ts`. The Flask backend is running at `http://127.0.0.1:5001` with CORS enabled. `@tanstack/react-query` is installed but unused.

## Approach: TanStack React Query

Chosen over manual `useEffect` + `useState` for automatic caching, retry, stale-while-revalidate, and reduced boilerplate. The library is already installed.

## Architecture

### File Structure

```
lib/
├── api.ts              # (new) fetch functions — pure async, no React
├── hooks/
│   └── index.ts        # (new) useQuery hooks wrapping api.ts
├── types.ts            # (new) type definitions matching backend responses
├── providers.tsx        # (new) QueryClientProvider wrapper
├── services/
│   └── index.ts        # (remove) replaced by hooks
├── mock/
│   └── data.ts         # (keep) no longer imported by anything
├── theme.tsx           # (unchanged)
└── utils.ts            # (unchanged)
```

### Data Flow

```
Backend API (port 5001)
    ↓ fetch()
lib/api.ts          — pure async functions returning Promise<T>
    ↓
lib/hooks/index.ts  — useQuery wrappers, manage cache/loading/error
    ↓
Components          — call hooks, render data/loading/error states
```

## Type Definitions (`lib/types.ts`)

Aligned to actual backend responses:

```typescript
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
  detail: Record<string, unknown>;  // JSONB object from backend
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

### Key Type Changes from Mock

| Field | Mock | Backend | Resolution |
|---|---|---|---|
| `AnomalyEvent.eventType` | `zscore_spike \| whale_alert \| volume_surge` | `zscore_spike \| whale_trade \| whale_directional_bias \| benford_violation` | Use backend types |
| `AnomalyEvent.detail` | `string` | JSONB object | Use `Record<string, unknown>` |
| `MarketStats` | `maxSwing, anomalyCount, currentPrice, priceChange, active` | `rowCount, firstTime, lastTime, avgPrice` | Use backend fields, redesign StatsBar |

## API Layer (`lib/api.ts`)

```typescript
const BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:5001";

async function fetchJson<T>(path: string): Promise<T> {
  const res = await fetch(`${BASE}${path}`);
  if (!res.ok) throw new Error(`API ${res.status}: ${path}`);
  return res.json();
}

export const api = {
  getMarkets:       () => fetchJson<Market[]>("/api/markets"),
  getPriceHistory:  (slug: string) => fetchJson<PricePoint[]>(`/api/markets/${slug}/prices`),
  getMarketStats:   (slug: string) => fetchJson<MarketStats>(`/api/markets/${slug}/stats`),
  getAnomalyEvents: (slug?: string) => {
    const params = slug ? `?slug=${slug}` : "";
    return fetchJson<AnomalyEvent[]>(`/api/anomalies${params}`);
  },
};
```

## React Query Hooks (`lib/hooks/index.ts`)

| Hook | Query Key | Stale Time | Notes |
|---|---|---|---|
| `useMarkets()` | `["markets"]` | 60s | Market list changes infrequently |
| `usePriceHistory(slug)` | `["prices", slug]` | 30s | Monitoring needs fresh data |
| `useMarketStats(slug)` | `["stats", slug]` | 30s | |
| `useAnomalyEvents(slug)` | `["anomalies", slug]` | 30s | |

All hooks return `{ data, isLoading, isError, error }`.

## Component Changes

### `app/layout.tsx`
- Wrap children with `QueryClientProvider` via `lib/providers.tsx`

### `app/page.tsx`
- `getMarkets()` → `useMarkets()`
- Handle loading state for initial market list

### `components/MarketSidebar.tsx`
- Receive markets as props from page (or use `useMarkets()` directly)
- No structural changes to UI

### `components/StatsBar.tsx`
- `getMarketStats(slug)` → `useMarketStats(slug)`
- Redesign cards to display backend fields:
  - **Average Price** — `avgPrice` formatted as percentage
  - **Data Points** — `rowCount`
  - **First Record** — `firstTime` formatted as date
  - **Last Record** — `lastTime` formatted as date

### `components/PriceChart.tsx`
- `getPriceHistory(slug)` → `usePriceHistory(slug)`
- `getAnomalyEvents(slug)` → `useAnomalyEvents(slug)`
- Update markPoint tooltip to render `detail` object (key-value pairs)

### `components/AnomalyFeed.tsx`
- `getAnomalyEvents(slug)` → `useAnomalyEvents(slug)`
- Extend `eventTypeConfig` for new event types:
  - `whale_trade` — Whale Trade (Wallet icon)
  - `whale_directional_bias` — Directional Bias (TrendingUp icon)
  - `benford_violation` — Benford Violation (BarChart icon)
- Render `detail` as structured key-value display instead of plain text

### Error & Loading States
- Each component handles its own loading/error
- Loading: text placeholder or skeleton
- Error: red text + message

## Environment Configuration

Add `.env.local`:
```
NEXT_PUBLIC_API_URL=http://127.0.0.1:5001
```

## Files Modified Summary

| File | Action |
|---|---|
| `lib/types.ts` | Create |
| `lib/api.ts` | Create |
| `lib/hooks/index.ts` | Create |
| `lib/providers.tsx` | Create |
| `.env.local` | Create |
| `app/layout.tsx` | Modify — add QueryClientProvider |
| `app/page.tsx` | Modify — use hooks |
| `components/MarketSidebar.tsx` | Modify — use hooks |
| `components/StatsBar.tsx` | Modify — use hooks + redesign cards |
| `components/PriceChart.tsx` | Modify — use hooks + adapt detail tooltip |
| `components/AnomalyFeed.tsx` | Modify — use hooks + new event types + detail rendering |
| `lib/services/index.ts` | Remove or empty |
