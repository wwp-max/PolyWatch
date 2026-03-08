# PolyWatch Frontend Implementation Plan

> **Last Updated:** 2026-03-08
> **Status:** All 10 original tasks DONE. Post-plan changes listed at bottom.
>
> **For AI:** Tasks 1-10 are completed and should NOT be re-executed. See "Post-Plan Changes" at the bottom for the current state of iterative improvements. Each change is marked `[DONE]` or `[TODO]`.

**Goal:** Build a professional dark-themed financial dashboard for PolyWatch using Next.js, ECharts, and shadcn/ui, with mock data and service layer isolation for future API integration.

**Architecture:** Single-page dashboard with 4 components (StatsBar, MarketSidebar, PriceChart, AnomalyFeed). Data flows through a service layer (`lib/services/index.ts`) that currently returns mock data. Future API integration requires modifying only this one file.

**Tech Stack:** Next.js 16.1.6 (App Router), TypeScript, Tailwind CSS v4, shadcn/ui, Apache ECharts 6, TanStack Query

---

### Task 1: Initialize Next.js Project

**Files:**
- Create: `polywatch-frontend/` (entire project scaffold)

**Step 1: Create Next.js project with pnpm**

Run:
```bash
pnpm dlx create-next-app@latest polywatch-frontend --typescript --tailwind --app --no-src-dir --use-pnpm --import-alias "@/*"
```

When prompted:
- Would you like to use ESLint? → **Yes**

Expected: A `polywatch-frontend/` directory is created with all config files.

**Step 2: Verify project runs**

Run:
```bash
cd polywatch-frontend && pnpm dev
```

Expected: Server starts at `http://localhost:3000`. Open in browser to see Next.js default page.

Stop the server with `Ctrl+C`.

**Step 3: Commit**

```bash
cd polywatch-frontend
git init
git add .
git commit -m "chore: initialize Next.js project with TypeScript and Tailwind"
```

---

### Task 2: Install Dependencies

**Files:**
- Modify: `polywatch-frontend/package.json`

**Step 1: Install ECharts and its React wrapper**

Run (from `polywatch-frontend/`):
```bash
pnpm add echarts echarts-for-react
```

**Step 2: Install TanStack Query**

Run:
```bash
pnpm add @tanstack/react-query
```

**Step 3: Install shadcn/ui CLI and initialize**

Run:
```bash
pnpm dlx shadcn@latest init
```

When prompted:
- Style: **Default**
- Base color: **Slate**
- CSS variables: **Yes**

**Step 4: Add shadcn/ui components we need**

Run:
```bash
pnpm dlx shadcn@latest add card badge scroll-area separator
```

**Step 5: Install lucide-react for icons**

Run:
```bash
pnpm add lucide-react
```

**Step 6: Verify everything still builds**

Run:
```bash
pnpm build
```

Expected: Build succeeds with no errors.

**Step 7: Commit**

```bash
git add .
git commit -m "chore: add ECharts, TanStack Query, shadcn/ui, and lucide-react"
```

---

### Task 3: Set Up Dark Theme and Global Layout

**Files:**
- Modify: `app/globals.css`
- Modify: `app/layout.tsx`
- Modify: `tailwind.config.ts` (if needed by shadcn)

**Step 1: Update globals.css for dark financial terminal theme**

Replace the content of `app/globals.css` with dark theme base styles. Keep Tailwind directives. Set `body` background to `gray-950`, text to `gray-100`.

**Step 2: Update layout.tsx**

Set the `<html>` tag to `className="dark"`. Update metadata title to "PolyWatch — Signal Analysis Dashboard". Use a monospace + sans-serif font combination.

**Step 3: Verify dark theme**

Run `pnpm dev`, open browser. Page should have dark background.

**Step 4: Commit**

```bash
git add .
git commit -m "feat: set up dark financial terminal theme"
```

---

### Task 4: Create Mock Data

**Files:**
- Create: `lib/mock/data.ts`

**Step 1: Create mock data file**

Create `lib/mock/data.ts` containing:

1. **3 markets** matching `data-pipeline-guide.md` Section 12:
   - `presidential-election-winner-2024` (historical, 7356 points simulated as ~200 points for demo)
   - `what-will-happen-before-gta-vi` (live, ~100 points)
   - `will-trump-acquire-greenland-before-2027` (live, ~100 points)

2. **Price history** for each market:
   - Array of `{ time: string (ISO 8601), price: number (0-1) }` objects.
   - Election market: price gradually rises from ~0.54 to ~0.95 with realistic volatility.
   - GTA VI market: fluctuates around 0.58.
   - Greenland market: fluctuates around 0.11.

3. **5-8 anomaly events** spread across the markets:
   - Each with `{ id, marketSlug, detectedAt, eventType, severity, detail }`.
   - Event types: `zscore_spike`, `whale_alert`, `volume_surge`.
   - Severities: `high`, `medium`, `low`.

**Step 2: Verify file has no TypeScript errors**

Run: `pnpm build`
Expected: No errors.

**Step 3: Commit**

```bash
git add .
git commit -m "feat: add realistic mock data for 3 markets and anomaly events"
```

---

### Task 5: Create Service Layer

**Files:**
- Create: `lib/services/index.ts`

**Step 1: Create service layer**

Create `lib/services/index.ts` that exports 3 functions:

```typescript
// These functions are the ONLY data source for all components.
// Currently they return mock data.
// Future: replace with fetch() calls to FastAPI.

export function getMarkets()                    // returns market list
export function getPriceHistory(slug: string)   // returns price array for a market
export function getAnomalyEvents(slug: string)  // returns anomaly events for a market
```

Each function imports from `@/lib/mock/data` and returns the relevant slice.

**Step 2: Verify no errors**

Run: `pnpm build`

**Step 3: Commit**

```bash
git add .
git commit -m "feat: add service layer with mock data isolation"
```

---

### Task 6: Build StatsBar Component

**Files:**
- Create: `components/StatsBar.tsx`

**Step 1: Create StatsBar**

A horizontal bar at the top showing 3-4 key metrics:
- Number of monitored markets
- Total data points across all markets
- Maximum single-hour price swing
- Current status indicator (green dot + "Live Monitoring")

Use shadcn `Card` component. Monospace font for numbers. Green/red accent colors.

**Step 2: Integrate into page.tsx**

Import and render `StatsBar` at top of `app/page.tsx`.

**Step 3: Verify in browser**

Run `pnpm dev`. StatsBar should appear at top with dark background and colored numbers.

**Step 4: Commit**

```bash
git add .
git commit -m "feat: add StatsBar component with summary statistics"
```

---

### Task 7: Build MarketSidebar Component

**Files:**
- Create: `components/MarketSidebar.tsx`

**Step 1: Create MarketSidebar**

A vertical sidebar on the left:
- List of markets from `getMarkets()`.
- Each item shows: market name (shortened), current price, up/down indicator.
- Clicking a market item sets it as "active" (highlighted).
- Use shadcn `ScrollArea` for overflow.

**Step 2: Add state management to page.tsx**

In `app/page.tsx`, add a `useState` for `selectedMarketSlug`. Pass it to `MarketSidebar` and future components.

**Step 3: Verify in browser**

Markets should appear in sidebar. Clicking one should highlight it.

**Step 4: Commit**

```bash
git add .
git commit -m "feat: add MarketSidebar with market selection"
```

---

### Task 8: Build PriceChart Component

**Files:**
- Create: `components/PriceChart.tsx`

**Step 1: Create PriceChart using ECharts**

The core visualization component:
- Line chart with `echarts-for-react`.
- X-axis: time. Y-axis: price (0-1).
- Dark theme colors (line: cyan/blue, background: transparent).
- `dataZoom` component at bottom for zoom/pan.
- Grid with subtle gridlines.
- Tooltip showing time and price on hover.

**Step 2: Add anomaly markers**

Use ECharts `markPoint` to render anomaly events as red circle symbols on the price line at the corresponding time. Each marker should show severity in tooltip.

**Step 3: Connect to service layer**

Component receives `slug` as prop, calls `getPriceHistory(slug)` and `getAnomalyEvents(slug)` from services.

**Step 4: Integrate into page.tsx**

Render `PriceChart` in the main content area, passing `selectedMarketSlug`.

**Step 5: Verify in browser**

Chart should render with price line, zoom control, and red anomaly markers. Switching markets in sidebar should update chart.

**Step 6: Commit**

```bash
git add .
git commit -m "feat: add PriceChart with ECharts, dataZoom, and anomaly markers"
```

---

### Task 9: Build AnomalyFeed Component

**Files:**
- Create: `components/AnomalyFeed.tsx`

**Step 1: Create AnomalyFeed**

A list of anomaly events below the chart:
- Each event shows: severity badge (colored), timestamp, event type, brief detail.
- Use shadcn `Badge` for severity (red for high, yellow for medium, blue for low).
- Use shadcn `ScrollArea` if list is long.
- Reverse chronological order (newest first).

**Step 2: Connect to service layer**

Receives `slug` as prop, calls `getAnomalyEvents(slug)`.

**Step 3: Integrate into page.tsx**

Render below PriceChart.

**Step 4: Verify in browser**

Anomaly list should appear, color-coded by severity. Switching markets should update the list.

**Step 5: Commit**

```bash
git add .
git commit -m "feat: add AnomalyFeed with severity-coded event list"
```

---

### Task 10: Final Layout Assembly and Polish

**Files:**
- Modify: `app/page.tsx`

**Step 1: Assemble final layout**

Arrange all 4 components in the grid layout defined in the design doc:
- Top: StatsBar (full width)
- Left: MarketSidebar (fixed width ~240px)
- Right top: PriceChart (flex grow)
- Right bottom: AnomalyFeed

Use Tailwind grid/flex utilities. Ensure responsive behavior on different screen sizes.

**Step 2: Add footer**

Simple footer: "PolyWatch — Polymarket Signal Analysis | CS6290 Project"

**Step 3: Final visual polish**

- Ensure consistent spacing and padding.
- Add subtle borders between sections using shadcn `Separator`.
- Verify dark theme is consistent across all components.

**Step 4: Full verification**

Run `pnpm dev`. Test:
- [ ] Dark theme renders correctly
- [ ] StatsBar shows statistics
- [ ] MarketSidebar lists 3 markets
- [ ] Clicking a market updates chart and anomaly feed
- [ ] PriceChart renders with zoom and anomaly markers
- [ ] AnomalyFeed shows color-coded events
- [ ] No console errors

Run `pnpm build` to verify production build succeeds.

**Step 5: Commit**

```bash
git add .
git commit -m "feat: assemble final dashboard layout with all components"
```

---

## Summary

| Task | Description | Key Output | Status |
|:---|:---|:---|:---|
| 1 | Initialize Next.js | Project scaffold | DONE |
| 2 | Install dependencies | ECharts, shadcn/ui, TanStack Query | DONE |
| 3 | Dark theme setup | Global dark financial terminal look | DONE |
| 4 | Mock data | Realistic data for 3 markets + anomalies | DONE |
| 5 | Service layer | Data isolation for future API swap | DONE |
| 6 | StatsBar | Top summary statistics bar | DONE |
| 7 | MarketSidebar | Left market selector | DONE |
| 8 | PriceChart | Core ECharts visualization with anomaly markers | DONE |
| 9 | AnomalyFeed | Anomaly event list | DONE |
| 10 | Final assembly | Complete dashboard layout and polish | DONE |

---

## Post-Plan Changes

Changes made after the original 10 tasks were completed. Each is marked `[DONE]` or `[TODO]`.

### `[DONE]` Light/Dark Theme Toggle
- Added `lib/theme.tsx` — `ThemeProvider` context + `useTheme()` hook.
- Added `components/ThemeToggle.tsx` — Sun/Moon icon button.
- Updated `app/layout.tsx` — wraps children in `ThemeProvider`, `<html className="dark" suppressHydrationWarning>`.
- Updated `app/globals.css` — added full light theme CSS variables (`:root` block) alongside dark (`.dark` block).
- Theme persists to `localStorage` key `polywatch-theme`. Default is dark.

### `[DONE]` Increased Font Sizes / Readability
- `StatsBar.tsx` — label `text-sm`, value `text-lg`.
- `MarketSidebar.tsx` — header `text-sm`, price `text-base`, change `text-sm`.
- `PriceChart.tsx` — axis labels 10→12, tooltip 12→14, price display 16→18, markPoint 11→13, dataZoom text 10→11.
- `AnomalyFeed.tsx` — header `text-sm`, count `text-xs`, event type `text-sm`, timestamp `text-xs`, detail `text-sm`.

### `[DONE]` PriceChart Theme-Aware Colors
- Imported `useTheme()` in `PriceChart.tsx`.
- All hardcoded dark-mode colors replaced with conditional `isDark ? darkColor : lightColor` for: axis lines, grid lines, tooltip background/text, accent color (`#38bdf8` vs `#2563eb`), area gradient, dataZoom.
- Added `isDark` to `useMemo` dependency array.

### `[DONE]` Chart Format: Line Chart (K-line Rejected)
- Decision: keep line chart, do not use candlestick/K-line.
- Reasons: data is single price points per hour (no OHLC), prediction market probabilities don't have meaningful candlestick patterns, line + anomaly markers is clearer for anomaly detection use case.

### `[DONE]` Layout Restructured for 100% Zoom
- Changed `h-screen` to `min-h-screen` (scrollable).
- Chart `h-[420px]`, anomaly feed `h-[280px]` (explicit heights).
- Sidebar `w-56` (from `w-64`), reduced padding throughout.

### `[DONE]` Full-Height Collapsible Sidebar
- `MarketSidebar` now occupies full left height (not below StatsBar).
- Added `collapsed` / `onToggleCollapse` props. Collapse to `w-14` (icon-only dots), expand to `w-56`.
- Toggle uses `PanelLeftClose` / `PanelLeftOpen` icons. `transition-[width] duration-200` animation.
- Top-level layout in `page.tsx` changed from vertical stacking to horizontal `flex h-screen`.

### `[DONE]` StatsBar → Per-Market Stats
- `StatsBar` now accepts `slug: string` prop instead of showing global stats.
- Shows 4 cards: Current Price (with 24h change %), Data Points, Max Price Swing, Anomalies Detected.
- Added `getMarketStats(slug)` function + `MarketStats` interface to `lib/services/index.ts`.
- Cards are vertically centered (icon top, label, value).

### `[DONE]` StatsBar Cards Centered
- Changed from horizontal layout (icon left, text right) to vertical centered (icon top, text center).

### `[TODO]` Future: Connect to FastAPI backend
- Replace mock data calls in `lib/services/index.ts` with `fetch()` to FastAPI endpoints.
- Activate TanStack Query (currently installed but unused).
- Add Zod validation for API responses.
