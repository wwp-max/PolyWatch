# M2 Data Pipeline Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build a Dockerized ETL pipeline that continuously fetches Polymarket price data into a TimescaleDB database, providing a real data source for the team's analysis and visualization modules.

**Architecture:** A `docker-compose.yml` orchestrates two services: a TimescaleDB instance and a Python `collector` service. The collector polls the Polymarket CLOB API every 5 minutes for a set of tracked markets and writes price data into TimescaleDB. The database schema is initialized automatically on first boot via `init.sql`. All M1 API logic (slug→token_id resolution, explicit timestamp fetching, stringified list parsing) is reused directly.

**Tech Stack:** Python 3.12, psycopg2-binary, requests, schedule, Docker Compose, TimescaleDB (PostgreSQL 16 extension)

**Venv:** `source /mnt/d/study/cityu/cs6920-privacy-enhangcing-technology/cs6290project/venv/bin/activate`

**Repo root:** `/mnt/d/study/cityu/cs6920-privacy-enhangcing-technology/cs6290project/PolyWatch/`

---

## Final Directory Layout

```
PolyWatch/
├── data_pipeline/
│   ├── docker-compose.yml
│   ├── db/
│   │   └── init.sql
│   ├── collector/
│   │   ├── Dockerfile
│   │   ├── requirements.txt
│   │   ├── main.py
│   │   ├── fetcher.py
│   │   └── db.py
│   └── README.md
├── docs/
│   └── plans/
│       └── 2026-03-06-m2-data-pipeline.md   ← this file
└── tests/
    └── data_pipeline/
        ├── test_fetcher.py
        └── test_db.py
```

---

## Task 1: Database Schema (`init.sql`)

**Files:**
- Create: `data_pipeline/db/init.sql`

**Step 1: Create the file**

```sql
-- data_pipeline/db/init.sql

CREATE TABLE IF NOT EXISTS markets (
    token_id   TEXT PRIMARY KEY,
    slug       TEXT NOT NULL,
    question   TEXT NOT NULL,
    active     BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS price_history (
    time       TIMESTAMPTZ NOT NULL,
    token_id   TEXT        NOT NULL REFERENCES markets(token_id),
    price      NUMERIC(6,4) NOT NULL
);

SELECT create_hypertable('price_history', 'time', if_not_exists => TRUE);

-- Unique constraint to prevent duplicate inserts on re-run
CREATE UNIQUE INDEX IF NOT EXISTS price_history_unique
    ON price_history (time, token_id);

CREATE TABLE IF NOT EXISTS anomaly_events (
    id          SERIAL PRIMARY KEY,
    token_id    TEXT        NOT NULL REFERENCES markets(token_id),
    detected_at TIMESTAMPTZ NOT NULL,
    event_type  TEXT        NOT NULL,
    severity    TEXT        NOT NULL,
    detail      JSONB
);
```

**Step 2: Verify SQL is valid (mental check)**

- `create_hypertable` requires TimescaleDB extension — it is pre-installed in the `timescale/timescaledb` image, no `CREATE EXTENSION` needed (it's in the image's default template).
- `UNIQUE INDEX` on `(time, token_id)` enables `ON CONFLICT DO NOTHING` upserts later.

**No commit yet — commit together with docker-compose in Task 3.**

---

## Task 2: Collector Python Modules

**Files:**
- Create: `data_pipeline/collector/fetcher.py`
- Create: `data_pipeline/collector/db.py`
- Create: `tests/data_pipeline/test_fetcher.py`
- Create: `tests/data_pipeline/test_db.py`

### 2a: `fetcher.py`

Reuses all M1 API logic. Fetches token_id from slug, then fetches price history for a time window.

```python
# data_pipeline/collector/fetcher.py
import json
import ast
import requests
from datetime import datetime, timezone

GAMMA_API_URL = "https://gamma-api.polymarket.com"
CLOB_API_URL  = "https://clob.polymarket.com"

HEADERS = {
    "User-Agent": "PolyWatch/2.0",
    "Accept": "application/json",
}


def resolve_token_id(slug: str) -> tuple[str, str] | tuple[None, None]:
    """
    Resolve market slug -> (token_id, question).
    Returns (None, None) if not found.
    """
    try:
        resp = requests.get(
            f"{GAMMA_API_URL}/events",
            params={"slug": slug},
            headers=HEADERS,
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()
        if not data or not data[0].get("markets"):
            return None, None

        market = data[0]["markets"][0]
        question = market["question"]

        clob_ids = market.get("clobTokenIds")
        if isinstance(clob_ids, str):
            try:
                clob_ids = json.loads(clob_ids)
            except json.JSONDecodeError:
                clob_ids = ast.literal_eval(clob_ids)

        if not clob_ids or not isinstance(clob_ids, list):
            return None, None

        return clob_ids[0], question

    except Exception as e:
        print(f"[fetcher] resolve_token_id error for {slug}: {e}")
        return None, None


def fetch_price_history(token_id: str, start_ts: int, end_ts: int) -> list[dict]:
    """
    Fetch price history for token_id between start_ts and end_ts (Unix timestamps).
    Returns list of {"time": datetime, "price": float} dicts.
    Returns [] on error or empty data.
    """
    try:
        resp = requests.get(
            f"{CLOB_API_URL}/prices-history",
            params={
                "market":   token_id,
                "startTs":  start_ts,
                "endTs":    end_ts,
                "fidelity": 60,
            },
            headers=HEADERS,
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()

        history = data.get("history", [])
        return [
            {
                "time":  datetime.fromtimestamp(point["t"], tz=timezone.utc),
                "price": float(point["p"]),
            }
            for point in history
        ]

    except Exception as e:
        print(f"[fetcher] fetch_price_history error for {token_id}: {e}")
        return []
```

### 2b: `db.py`

Handles all database interactions: upsert markets, bulk insert price rows.

```python
# data_pipeline/collector/db.py
import os
import psycopg2
import psycopg2.extras
from datetime import datetime, timezone

DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql://polywatch:polywatch@localhost:5432/polywatch",
)


def get_connection():
    return psycopg2.connect(DATABASE_URL)


def upsert_market(conn, token_id: str, slug: str, question: str) -> None:
    """Insert market if not exists. Ignore if already present."""
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO markets (token_id, slug, question)
            VALUES (%s, %s, %s)
            ON CONFLICT (token_id) DO NOTHING
            """,
            (token_id, slug, question),
        )
    conn.commit()


def insert_price_rows(conn, token_id: str, rows: list[dict]) -> int:
    """
    Bulk insert price rows. Silently skips duplicates.
    Returns number of rows actually inserted.
    """
    if not rows:
        return 0

    data = [(r["time"], token_id, r["price"]) for r in rows]

    with conn.cursor() as cur:
        psycopg2.extras.execute_values(
            cur,
            """
            INSERT INTO price_history (time, token_id, price)
            VALUES %s
            ON CONFLICT (time, token_id) DO NOTHING
            """,
            data,
        )
        inserted = cur.rowcount

    conn.commit()
    return inserted


def get_latest_timestamp(conn, token_id: str) -> datetime | None:
    """Return the most recent time stored for token_id, or None."""
    with conn.cursor() as cur:
        cur.execute(
            "SELECT MAX(time) FROM price_history WHERE token_id = %s",
            (token_id,),
        )
        result = cur.fetchone()
        return result[0] if result and result[0] else None
```

### 2c: Tests for `fetcher.py`

```python
# tests/data_pipeline/test_fetcher.py
"""
Tests for fetcher.py — uses mocking to avoid real network calls.
"""
from unittest.mock import patch, MagicMock
from datetime import datetime, timezone
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../data_pipeline/collector"))

from fetcher import resolve_token_id, fetch_price_history


class TestResolveTokenId:
    def test_returns_token_id_and_question_on_success(self):
        mock_response = MagicMock()
        mock_response.json.return_value = [{
            "markets": [{
                "question": "Will X happen?",
                "clobTokenIds": '["abc123", "def456"]',  # stringified list
            }]
        }]
        mock_response.raise_for_status = MagicMock()

        with patch("fetcher.requests.get", return_value=mock_response):
            token_id, question = resolve_token_id("test-slug")

        assert token_id == "abc123"
        assert question == "Will X happen?"

    def test_returns_none_on_empty_response(self):
        mock_response = MagicMock()
        mock_response.json.return_value = []
        mock_response.raise_for_status = MagicMock()

        with patch("fetcher.requests.get", return_value=mock_response):
            token_id, question = resolve_token_id("nonexistent-slug")

        assert token_id is None
        assert question is None

    def test_handles_network_error_gracefully(self):
        with patch("fetcher.requests.get", side_effect=Exception("timeout")):
            token_id, question = resolve_token_id("any-slug")

        assert token_id is None
        assert question is None


class TestFetchPriceHistory:
    def test_returns_list_of_dicts_with_time_and_price(self):
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "history": [
                {"t": 1730419200, "p": "0.512"},
                {"t": 1730422800, "p": "0.531"},
            ]
        }
        mock_response.raise_for_status = MagicMock()

        with patch("fetcher.requests.get", return_value=mock_response):
            rows = fetch_price_history("token123", 1730419200, 1730422800)

        assert len(rows) == 2
        assert rows[0]["price"] == 0.512
        assert isinstance(rows[0]["time"], datetime)
        assert rows[0]["time"].tzinfo == timezone.utc

    def test_returns_empty_list_on_empty_history(self):
        mock_response = MagicMock()
        mock_response.json.return_value = {"history": []}
        mock_response.raise_for_status = MagicMock()

        with patch("fetcher.requests.get", return_value=mock_response):
            rows = fetch_price_history("token123", 0, 1)

        assert rows == []

    def test_returns_empty_list_on_error(self):
        with patch("fetcher.requests.get", side_effect=Exception("network error")):
            rows = fetch_price_history("token123", 0, 1)

        assert rows == []
```

### 2d: Tests for `db.py`

```python
# tests/data_pipeline/test_db.py
"""
Tests for db.py — uses a real TimescaleDB connection.
Requires: docker compose up -d timescaledb  (from data_pipeline/)
Set env: DATABASE_URL=postgresql://polywatch:polywatch@localhost:5432/polywatch
"""
import os
import pytest
from datetime import datetime, timezone

# Allow running tests from repo root
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../data_pipeline/collector"))

DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql://polywatch:polywatch@localhost:5432/polywatch",
)


@pytest.fixture
def conn():
    """Provide a test DB connection, clean up test data after each test."""
    import psycopg2
    c = psycopg2.connect(DATABASE_URL)
    yield c
    # Cleanup: remove test data
    with c.cursor() as cur:
        cur.execute("DELETE FROM price_history WHERE token_id = 'test-token-001'")
        cur.execute("DELETE FROM markets WHERE token_id = 'test-token-001'")
    c.commit()
    c.close()


class TestUpsertMarket:
    def test_inserts_new_market(self, conn):
        from db import upsert_market, get_connection
        upsert_market(conn, "test-token-001", "test-slug", "Test Question?")
        with conn.cursor() as cur:
            cur.execute("SELECT slug, question FROM markets WHERE token_id = 'test-token-001'")
            row = cur.fetchone()
        assert row == ("test-slug", "Test Question?")

    def test_is_idempotent_on_duplicate(self, conn):
        from db import upsert_market
        upsert_market(conn, "test-token-001", "test-slug", "Test Question?")
        upsert_market(conn, "test-token-001", "test-slug", "Test Question?")  # no error
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM markets WHERE token_id = 'test-token-001'")
            count = cur.fetchone()[0]
        assert count == 1


class TestInsertPriceRows:
    def test_inserts_rows_and_returns_count(self, conn):
        from db import upsert_market, insert_price_rows
        upsert_market(conn, "test-token-001", "test-slug", "Test Question?")

        rows = [
            {"time": datetime(2024, 11, 1, 0, 0, tzinfo=timezone.utc), "price": 0.51},
            {"time": datetime(2024, 11, 1, 1, 0, tzinfo=timezone.utc), "price": 0.53},
        ]
        inserted = insert_price_rows(conn, "test-token-001", rows)
        assert inserted == 2

    def test_skips_duplicates_silently(self, conn):
        from db import upsert_market, insert_price_rows
        upsert_market(conn, "test-token-001", "test-slug", "Test Question?")

        rows = [{"time": datetime(2024, 11, 1, 0, 0, tzinfo=timezone.utc), "price": 0.51}]
        insert_price_rows(conn, "test-token-001", rows)
        inserted = insert_price_rows(conn, "test-token-001", rows)  # duplicate
        assert inserted == 0

    def test_returns_zero_for_empty_rows(self, conn):
        from db import insert_price_rows
        inserted = insert_price_rows(conn, "test-token-001", [])
        assert inserted == 0


class TestGetLatestTimestamp:
    def test_returns_none_when_no_data(self, conn):
        from db import upsert_market, get_latest_timestamp
        upsert_market(conn, "test-token-001", "test-slug", "Test Question?")
        result = get_latest_timestamp(conn, "test-token-001")
        assert result is None

    def test_returns_most_recent_time(self, conn):
        from db import upsert_market, insert_price_rows, get_latest_timestamp
        upsert_market(conn, "test-token-001", "test-slug", "Test Question?")

        rows = [
            {"time": datetime(2024, 11, 1, 0, 0, tzinfo=timezone.utc), "price": 0.51},
            {"time": datetime(2024, 11, 1, 2, 0, tzinfo=timezone.utc), "price": 0.55},
        ]
        insert_price_rows(conn, "test-token-001", rows)
        latest = get_latest_timestamp(conn, "test-token-001")
        assert latest.replace(tzinfo=timezone.utc) == datetime(2024, 11, 1, 2, 0, tzinfo=timezone.utc)
```

**Step 3: Run fetcher tests (no DB needed)**

```bash
cd /mnt/d/study/cityu/cs6920-privacy-enhangcing-technology/cs6290project/PolyWatch
source /mnt/d/study/cityu/cs6920-privacy-enhangcing-technology/cs6290project/venv/bin/activate
pip install pytest psycopg2-binary schedule --quiet
pytest tests/data_pipeline/test_fetcher.py -v
```

Expected: 6 tests PASS

**Step 4: Commit**

```bash
git add data_pipeline/collector/fetcher.py data_pipeline/collector/db.py
git add tests/data_pipeline/test_fetcher.py tests/data_pipeline/test_db.py
git commit -m "feat(data-pipeline): add fetcher and db modules with tests"
```

---

## Task 3: Docker Compose + Dockerfile

**Files:**
- Create: `data_pipeline/docker-compose.yml`
- Create: `data_pipeline/collector/Dockerfile`
- Create: `data_pipeline/collector/requirements.txt`

### 3a: `docker-compose.yml`

```yaml
# data_pipeline/docker-compose.yml
services:
  timescaledb:
    image: timescale/timescaledb:latest-pg16
    environment:
      POSTGRES_DB:       polywatch
      POSTGRES_USER:     polywatch
      POSTGRES_PASSWORD: polywatch
    ports:
      - "5432:5432"
    volumes:
      - timescale_data:/var/lib/postgresql/data
      - ./db/init.sql:/docker-entrypoint-initdb.d/init.sql
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U polywatch -d polywatch"]
      interval: 5s
      timeout: 5s
      retries: 10

  collector:
    build: ./collector
    depends_on:
      timescaledb:
        condition: service_healthy
    environment:
      DATABASE_URL: postgresql://polywatch:polywatch@timescaledb:5432/polywatch
      POLL_INTERVAL_SECONDS: "300"
    restart: unless-stopped

volumes:
  timescale_data:
```

**Key decisions:**
- `healthcheck` on timescaledb prevents the collector from starting before the DB is ready.
- `condition: service_healthy` in `depends_on` waits for healthcheck to pass.
- `POLL_INTERVAL_SECONDS` is an env var so it can be overridden for testing (e.g., set to 10).

### 3b: `collector/Dockerfile`

```dockerfile
# data_pipeline/collector/Dockerfile
FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["python", "main.py"]
```

### 3c: `collector/requirements.txt`

```
requests==2.32.3
psycopg2-binary==2.9.10
schedule==1.2.2
```

**Step 1: Verify versions are available**

```bash
pip index versions psycopg2-binary 2>/dev/null | head -2
pip index versions schedule 2>/dev/null | head -2
```

**Step 2: Commit**

```bash
git add data_pipeline/docker-compose.yml
git add data_pipeline/collector/Dockerfile
git add data_pipeline/collector/requirements.txt
git add data_pipeline/db/init.sql
git commit -m "feat(data-pipeline): add docker-compose, Dockerfile, and DB schema"
```

---

## Task 4: Collector Main Loop (`main.py`)

**Files:**
- Create: `data_pipeline/collector/main.py`

```python
# data_pipeline/collector/main.py
import os
import time
import schedule
from datetime import datetime, timezone, timedelta

from fetcher import resolve_token_id, fetch_price_history
from db import get_connection, upsert_market, insert_price_rows, get_latest_timestamp

# ── Markets to monitor ──────────────────────────────────────────────────────
# Add/remove slugs here to change which markets are tracked.
TRACKED_MARKETS = [
    "presidential-election-winner-2024",
    "will-there-be-a-us-recession-in-2025",
    "super-bowl-lix-winner",
]

POLL_INTERVAL = int(os.environ.get("POLL_INTERVAL_SECONDS", "300"))

# How far back to fetch if a market has never been seen before (days)
INITIAL_LOOKBACK_DAYS = 30


def collect_once():
    """Run one full collection pass across all tracked markets."""
    print(f"[collector] Starting collection pass at {datetime.now(timezone.utc).isoformat()}")

    try:
        conn = get_connection()
    except Exception as e:
        print(f"[collector] DB connection failed: {e}")
        return

    for slug in TRACKED_MARKETS:
        try:
            token_id, question = resolve_token_id(slug)
            if not token_id:
                print(f"[collector] Could not resolve slug: {slug}, skipping.")
                continue

            upsert_market(conn, token_id, slug, question)

            latest = get_latest_timestamp(conn, token_id)
            if latest:
                start_ts = int(latest.timestamp()) + 1  # +1 to avoid re-fetching last point
            else:
                start_ts = int((datetime.now(timezone.utc) - timedelta(days=INITIAL_LOOKBACK_DAYS)).timestamp())

            end_ts = int(datetime.now(timezone.utc).timestamp())

            if start_ts >= end_ts:
                print(f"[collector] {slug}: already up to date.")
                continue

            rows = fetch_price_history(token_id, start_ts, end_ts)
            inserted = insert_price_rows(conn, token_id, rows)
            print(f"[collector] {slug}: fetched {len(rows)} points, inserted {inserted} new rows.")

        except Exception as e:
            print(f"[collector] Error processing {slug}: {e}")

    conn.close()
    print(f"[collector] Pass complete.")


def main():
    print(f"[collector] PolyWatch collector starting. Poll interval: {POLL_INTERVAL}s")
    collect_once()  # Run immediately on startup
    schedule.every(POLL_INTERVAL).seconds.do(collect_once)
    while True:
        schedule.run_pending()
        time.sleep(1)


if __name__ == "__main__":
    main()
```

**Step 1: Verify logic (mental walkthrough)**

- On first run: `get_latest_timestamp` returns None → fetches last 30 days of data.
- On subsequent runs: fetches only data newer than last stored point → incremental, no duplicates.
- `ON CONFLICT DO NOTHING` in `insert_price_rows` is a safety net even if logic overlaps.

**Step 2: Commit**

```bash
git add data_pipeline/collector/main.py
git commit -m "feat(data-pipeline): add collector main loop with incremental fetching"
```

---

## Task 5: Smoke Test — Start the Stack

**Step 1: Start DB only first**

```bash
cd /mnt/d/study/cityu/cs6920-privacy-enhangcing-technology/cs6290project/PolyWatch/data_pipeline
docker compose up -d timescaledb
```

Wait ~10 seconds, then check:

```bash
docker compose ps
```

Expected: `timescaledb` shows `healthy`.

**Step 2: Verify schema was applied**

```bash
docker exec -it data_pipeline-timescaledb-1 psql -U polywatch -d polywatch -c "\dt"
```

Expected output (3 tables):
```
 Schema |      Name       | Type  |   Owner
--------+-----------------+-------+-----------
 public | anomaly_events  | table | polywatch
 public | markets         | table | polywatch
 public | price_history   | table | polywatch
```

**Step 3: Run DB integration tests**

```bash
cd /mnt/d/study/cityu/cs6920-privacy-enhangcing-technology/cs6290project/PolyWatch
source /mnt/d/study/cityu/cs6920-privacy-enhangcing-technology/cs6290project/venv/bin/activate
DATABASE_URL=postgresql://polywatch:polywatch@localhost:5432/polywatch pytest tests/data_pipeline/test_db.py -v
```

Expected: 7 tests PASS

**Step 4: Start full stack**

```bash
cd data_pipeline
docker compose up -d
docker compose logs -f collector
```

Expected log output:
```
[collector] PolyWatch collector starting. Poll interval: 300s
[collector] Starting collection pass at 2026-03-06T...
[collector] presidential-election-winner-2024: fetched 135 points, inserted 135 new rows.
[collector] will-there-be-a-us-recession-in-2025: fetched N points, inserted N new rows.
...
[collector] Pass complete.
```

**Step 5: Verify data in DB**

```bash
docker exec -it data_pipeline-timescaledb-1 psql -U polywatch -d polywatch \
  -c "SELECT m.slug, COUNT(ph.time) as rows FROM markets m JOIN price_history ph ON m.token_id = ph.token_id GROUP BY m.slug;"
```

Expected: each tracked market shows a row count > 0.

**Step 6: Commit**

```bash
git add docs/plans/2026-03-06-m2-data-pipeline.md
git commit -m "docs: add M2 data pipeline implementation plan"
```

---

## Task 6: README for `data_pipeline/`

**Files:**
- Create: `data_pipeline/README.md`

```markdown
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
postgresql://polywatch:polywatch@localhost:5432/polywatch
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
```

**Step 1: Commit**

```bash
git add data_pipeline/README.md
git commit -m "docs(data-pipeline): add README with quick start and schema reference"
```

---

## Task 7: Update repo-level `requirements.txt`

**Files:**
- Modify: `requirements.txt`

Current content:
```
py-clob-client
requests
pandas
```

Updated content:
```
py-clob-client
requests
pandas
psycopg2-binary
schedule
numpy
```

(`numpy` is needed by `core_analysis/zscore_detector.py` which was already in the repo.)

**Step 1: Update the file, then commit**

```bash
git add requirements.txt
git commit -m "chore: update requirements.txt with M2 dependencies"
```

---

## Task 8: Final Verification

**Step 1: Run all tests**

```bash
cd /mnt/d/study/cityu/cs6920-privacy-enhangcing-technology/cs6290project/PolyWatch
source /mnt/d/study/cityu/cs6920-privacy-enhangcing-technology/cs6290project/venv/bin/activate
DATABASE_URL=postgresql://polywatch:polywatch@localhost:5432/polywatch pytest tests/ -v
```

Expected: all tests PASS (6 fetcher unit tests + 7 db integration tests = 13 total)

**Step 2: Check git log**

```bash
git log --oneline -8
```

Expected:
```
<hash> chore: update requirements.txt with M2 dependencies
<hash> docs(data-pipeline): add README with quick start and schema reference
<hash> docs: add M2 data pipeline implementation plan
<hash> feat(data-pipeline): add collector main loop with incremental fetching
<hash> feat(data-pipeline): add docker-compose, Dockerfile, and DB schema
<hash> feat(data-pipeline): add fetcher and db modules with tests
<hash> Create whale_alert.py          ← teammate commit
...
```

**Step 3: Capture Evidence Pack screenshots**

For the Individual Evidence Pack, take screenshots of:
1. `docker compose ps` showing both services `healthy`/`running`
2. `docker compose logs collector` showing "inserted N new rows"
3. psql query showing row counts per market
4. `pytest tests/ -v` showing all tests PASS
5. `git log --oneline` showing your commits

---

## Rollback / Troubleshooting

| Problem | Fix |
|---------|-----|
| `timescaledb` not healthy after 30s | `docker compose logs timescaledb` — check for port 5432 conflict. Stop any local postgres first. |
| `collector` exits immediately | `docker compose logs collector` — likely DB URL wrong or schema not applied yet |
| `create_hypertable` error in init.sql | The `timescaledb` extension may not be loaded. Add `CREATE EXTENSION IF NOT EXISTS timescaledb;` as first line of init.sql |
| Port 5432 already in use | Change host port in docker-compose.yml: `"5433:5432"` and update DATABASE_URL accordingly |
| Fetcher returns 0 rows for a slug | Market may be closed — check slug is correct on polymarket.com |
