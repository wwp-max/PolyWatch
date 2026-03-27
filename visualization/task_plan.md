# PolyWatch API Integration — Task Plan

**Goal:** Replace all mock data in the frontend with real backend API calls using TanStack React Query.

**Constraint:** No backend code changes. Backend runs at `http://127.0.0.1:5001`.

**Design Doc:** `docs/plans/2026-03-27-api-integration-design.md`
**Implementation Plan:** `docs/plans/2026-03-27-api-integration-plan.md`

---

## Phases

### Phase 1: Foundation Layer (Tasks 1-4)
Create types, API fetch layer, QueryProvider, and hooks.

| Task | Description | Status |
|------|-------------|--------|
| 1 | Create `lib/types.ts` — type definitions aligned to backend | pending |
| 2 | Create `lib/api.ts` + `.env.local` — fetch functions | pending |
| 3 | Create `lib/providers.tsx` + modify `app/layout.tsx` — QueryProvider | pending |
| 4 | Create `lib/hooks/index.ts` — React Query hooks | pending |

### Phase 2: Component Migration (Tasks 5-9)
Migrate all components from sync mock data to async hooks.

| Task | Description | Status |
|------|-------------|--------|
| 5 | Modify `app/page.tsx` — useMarkets hook + loading/error states | pending |
| 6 | Modify `components/MarketSidebar.tsx` — useMarkets hook | pending |
| 7 | Rewrite `components/StatsBar.tsx` — useMarketStats + redesign cards | pending |
| 8 | Modify `components/PriceChart.tsx` — usePriceHistory + useAnomalyEvents | pending |
| 9 | Modify `components/AnomalyFeed.tsx` — useAnomalyEvents + new event types | pending |

### Phase 3: Cleanup & Verification (Tasks 10-11)
Remove old service layer, full integration test.

| Task | Description | Status |
|------|-------------|--------|
| 10 | Clean up `lib/services/index.ts` | pending |
| 11 | Full integration verification — build + manual test | pending |

---

## Errors Encountered

| Error | Attempt | Resolution |
|-------|---------|------------|
| (none yet) | | |
