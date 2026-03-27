# Findings

## Backend API Responses (verified via curl)

### GET /api/markets
Returns 6 markets. Fields: `slug, question, active, lastPrice, prevPrice`.

### GET /api/markets/<slug>/prices
Returns array of `{time: ISO8601, price: float}`. Hourly data.

### GET /api/markets/<slug>/stats
Returns `{slug, question, rowCount, firstTime, lastTime, avgPrice}`.

### GET /api/anomalies
Returns array of anomaly events. `detail` is a JSONB object (not string).
Event types found: `zscore_spike`, `whale_trade`, `whale_directional_bias`, `benford_violation`.

### Key Differences from Mock
- `AnomalyEvent.eventType`: mock had `whale_alert`, `volume_surge`; backend has `whale_trade`, `whale_directional_bias`, `benford_violation`
- `AnomalyEvent.detail`: mock was string, backend is JSONB object
- `MarketStats`: backend returns `rowCount/avgPrice/firstTime/lastTime`, mock had `maxSwing/anomalyCount/currentPrice/priceChange/active`
- Backend has 6 markets, mock had 3

## Design Decisions
- Use TanStack React Query (already installed as dependency)
- All components redesigned to match backend fields exactly
- Three-layer architecture: api.ts → hooks → components
