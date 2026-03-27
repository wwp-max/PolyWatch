# PolyWatch Frontend Design Document

> Date: 2026-03-08
> Last Updated: 2026-03-08
> Status: **Implemented** — all sections below reflect the current codebase.
> Author: Frontend Team (AI-assisted)

---

## 1. Context

### Project
PolyWatch — Polymarket signal analysis: detect unusual odds movements empirically.

### Background
- **Milestone 1 (completed):** Streamlit prototype with mock data. Demonstrated market list, price chart, and anomaly event display.
- **Milestone 2 (current):** Professional frontend rebuild using modern web stack. Still uses mock data but must be structured for seamless future API integration.
- **Backend status:** Data pipeline exists (TimescaleDB + Python collector), documented in `data-pipeline-guide.md`. No HTTP API yet. Backend data format may change significantly.
- **Algorithm team:** Anomaly detection algorithm in development, no documentation yet.

### Target Users
Course reviewers and team members for project demonstration. Priority: visual impact, data visualization completeness, professional appearance.

---

## 2. Technical Decision

### Chosen: Next.js + ECharts + shadcn/ui

| Component | Technology | Version | Purpose |
|:---|:---|:---|:---|
| Framework | Next.js (App Router) | 16.1.6 | Page structure, routing, SSR |
| Language | TypeScript | — | Type safety, better AI code generation |
| Styling | Tailwind CSS | v4 | Rapid dark-theme UI development (CSS variables, no tailwind.config.ts) |
| UI Components | shadcn/ui | — | Professional pre-built components (card, badge, scroll-area, separator, button) |
| Charts | Apache ECharts + echarts-for-react | v6 | High-performance time-series visualization |
| Data Fetching | TanStack Query | — | Caching, auto-refresh, error handling (installed, not yet used) |
| Icons | lucide-react | — | Consistent icon set |
| Package Manager | pnpm | 10.30.3 | — |
| Node.js | — | v24.14.0 | — |

### Rejected Alternatives
- **Vite + Recharts:** Recharts cannot handle 7000+ data points well; lacks markPoint/markArea for anomaly highlighting.
- **Streamlit (keep):** Poor interactivity, limited UI customization, not suitable for professional presentation.
- **Candlestick/K-line chart:** Rejected because data is single price points per hour (no OHLC), prediction market probabilities don't have meaningful candlestick patterns, and line + anomaly markers is clearer for the anomaly detection use case.

---

## 3. Architecture

### Core Principle: Service Layer Isolation

```
mock/data.ts         ← Mock data (current phase)
services/index.ts    ← Data source switch (only file to change when adding API)
components/          ← UI components (never change due to backend changes)
```

- Components only import from `services/index.ts`.
- Components never directly access mock data.
- When FastAPI is added later, only `services/index.ts` is modified.
- If backend field names differ from mock, a transform is added inside `services/index.ts`.

### File Structure

```
polywatch-frontend/
├── app/
│   ├── layout.tsx          # Root layout (ThemeProvider, fonts, suppressHydrationWarning)
│   ├── page.tsx            # Single-page dashboard: sidebar state + right panel assembly
│   └── globals.css         # Tailwind v4 theme via CSS variables (light + dark)
├── components/
│   ├── MarketSidebar.tsx   # Left: full-height collapsible market list
│   ├── PriceChart.tsx      # Center: ECharts line chart + anomaly markers (theme-aware)
│   ├── AnomalyFeed.tsx     # Below chart: anomaly event list
│   ├── StatsBar.tsx        # Per-market statistics (4 cards)
│   ├── ThemeToggle.tsx     # Sun/Moon toggle button
│   └── ui/                 # shadcn components (badge, button, card, scroll-area, separator)
├── lib/
│   ├── mock/
│   │   └── data.ts         # Mock data (3 markets, price series, 7 anomaly events)
│   ├── services/
│   │   └── index.ts        # Service layer: getMarkets, getPriceHistory, getAnomalyEvents, getMarketStats
│   ├── theme.tsx            # ThemeProvider context + useTheme hook
│   └── utils.ts            # shadcn cn() utility
├── package.json
└── tsconfig.json
```

---

## 4. Page Layout

Single-page dashboard with dark/light financial terminal theme. Sidebar occupies the full left height and is collapsible.

```
┌─────────────┬─────────────────────────────────────────────┐
│             │  Header: "PolyWatch" + theme toggle          │
│  Market     ├─────────────────────────────────────────────┤
│  Sidebar    │  Market title + slug + status                │
│  (full      ├─────────────────────────────────────────────┤
│  height,    │  StatsBar (per-market, 4 centered cards)     │
│  collaps-   │  [Price] [Data Points] [Max Swing] [Alerts]  │
│  ible       ├─────────────────────────────────────────────┤
│  w-56 /     │  PriceChart (420px, ECharts line chart)      │
│  w-14)      │  - dataZoom, anomaly markPoints              │
│             │  - theme-aware colors (light/dark)           │
│  << toggle  ├─────────────────────────────────────────────┤
│             │  AnomalyFeed (280px, scrollable list)        │
│             │  [HIGH] Z-Score Spike: 4.2 ...               │
│             ├─────────────────────────────────────────────┤
│             │  Footer                                      │
└─────────────┴─────────────────────────────────────────────┘
```

---

## 5. Component Specifications

### StatsBar
- **Input:** `slug: string` — the currently selected market.
- **Data source:** `getMarketStats(slug)` from service layer.
- **Display:** 4 centered cards — Current Price (with 24h change), Data Points, Max Price Swing, Anomalies Detected.
- **Layout:** `grid grid-cols-2 xl:grid-cols-4`, cards vertically centered (icon on top, label, value).

### MarketSidebar
- **Input:** `selectedSlug`, `onSelectMarket`, `collapsed`, `onToggleCollapse`.
- **Behavior:** Click a market to update all right-side components. Toggle button collapses to `w-14` (icon-only dots) or expands to `w-56` (full list). Animated transition.
- **Visual:** Active market highlighted with `bg-accent`. Green/red price change indicator. Active status dot per market.

### PriceChart
- **Input:** `slug: string`.
- **Data source:** `getPriceHistory(slug)` + `getAnomalyEvents(slug)`.
- **Chart type:** ECharts line chart via `echarts-for-react` (dynamic import, `ssr: false`).
- **Features:**
  - X-axis: time, Y-axis: probability (0-1) as percentage.
  - `dataZoom` (slider + inside) for pan/zoom.
  - Anomaly events as colored `markPoint` circles (red=high, yellow=medium, blue=low).
  - Tooltip with time + price percentage.
  - All colors are **theme-aware** via `useTheme()` hook — adapts to light/dark mode.

### AnomalyFeed
- **Input:** `slug: string`.
- **Data source:** `getAnomalyEvents(slug)`.
- **Display:** Reverse-chronological scrollable list.
- **Visual:** Color-coded severity badges (red=high, yellow=medium, blue=low). Icons per event type (AlertTriangle, Wallet, Waves).

### ThemeToggle
- **Behavior:** Toggles between light and dark theme. Persists to `localStorage` key `polywatch-theme`. Uses Sun/Moon icons from lucide-react.

---

## 6. Interaction Flow

1. User clicks a market in **MarketSidebar** (e.g., "2024 US Election").
2. **StatsBar** updates to show that market's statistics (price, data points, max swing, anomaly count).
3. **PriceChart** updates to show that market's price curve with anomaly markers.
4. **AnomalyFeed** updates to show that market's anomaly events.
5. User can zoom/pan the chart using **dataZoom**.
6. User hovers over anomaly markers to see detail tooltip.
7. User can collapse/expand the sidebar via the toggle button.
8. User can switch between light/dark theme via **ThemeToggle**.

---

## 7. Visual Style

- **Theme:** Dark mode default (Bloomberg/TradingView inspired). Light mode available via toggle.
- **Dark:** Background `oklch(0.12 ...)`, cards `oklch(0.16 ...)`. Light text.
- **Light:** Background `oklch(0.985 ...)`, cards white. Dark text.
- **Accent colors (dark):** Green `#22c55e`, Red `#ef4444`, Yellow `#eab308`, Blue `#38bdf8`.
- **Accent colors (light):** Green `#16a34a`, Red `#dc2626`, Yellow `#ca8a04`, Blue `#2563eb`.
- **Font:** Monospace for numbers/data, sans-serif for labels.
- **Tailwind CSS v4:** All theming via CSS variables in `globals.css`. No `tailwind.config.ts`.

---

## 8. Future API Integration Path

When backend provides HTTP API (e.g., FastAPI):

1. Write fetch logic in `services/index.ts` (replace mock imports with `fetch()` calls).
2. If field names differ, add transform mapping in the same file.
3. All components remain unchanged.
4. Optionally add Zod runtime validation for data safety.
5. Switch TanStack Query from unused to active (wrap service calls in `useQuery`).

**Estimated effort to switch from mock to real API: modify 1 file (`lib/services/index.ts`).**
