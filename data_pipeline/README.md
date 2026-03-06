# data_pipeline

Automated data collection pipeline for PolyWatch M2.

## What it does

Polls the Polymarket CLOB API every 5 minutes and stores price history in a
TimescaleDB (PostgreSQL) database. Provides real market data for the
`core_analysis` (anomaly detection) and visualization modules.

## Quick Start

### Prerequisites
- Docker Desktop with WSL2 integration enabled
- Both images pulled: `timescale/timescaledb:latest-pg16`, `python:3.12-slim`

### Start

```bash
cd data_pipeline
docker compose up -d
docker compose logs -f collector   # watch live collection
```

### Stop

```bash
docker compose down          # stop, keep data volume
docker compose down -v       # stop, DELETE data volume
```

## Database Schema

| Table | Description |
|-------|-------------|
| `markets` | Market metadata (slug, question, token_id) |
| `price_history` | TimescaleDB hypertable — time-series prices |
| `anomaly_events` | Detected anomalies (written by core_analysis module) |

## Connecting to the DB

From host machine (with stack running):
```
postgresql://polywatch:polywatch@localhost:5433/polywatch
```

From another Docker container:
```
postgresql://polywatch:polywatch@timescaledb:5432/polywatch
```

## Tracked Markets

Edit `collector/main.py` → `TRACKED_MARKETS` list to add/remove markets.
Uses Polymarket event slugs (the part of the URL after `polymarket.com/event/`).

## Configuration

| Env Var | Default | Description |
|---------|---------|-------------|
| `DATABASE_URL` | (see above) | PostgreSQL connection string |
| `POLL_INTERVAL_SECONDS` | `300` | How often to poll (seconds) |
