# M3: Data Quality Report + DB Interface Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Create shared DB interface (`core_analysis/db_interface.py`) for all team members + data quality report module + CLI tool, enabling Member C (algorithms), Member D (forensics), and Member E (frontend) to access real DB data instead of CSVs/mock data.

**Architecture:** One shared `db_interface.py` module that returns data matching the frontend's TypeScript contract (Market, PricePoint, AnomalyEvent types). A `data_quality.py` module analyzes pipeline output completeness/consistency. A CLI script generates human-readable reports.

**Tech Stack:** Python, psycopg2 (existing), pandas (existing), numpy (existing)

---

## Key Finding: Frontend Data Contract (from Member E)

The Next.js frontend (`visualization/polywatch-frontend/lib/services/index.ts`) expects:

```typescript
Market { slug: string, question: string, active: boolean, lastPrice: number, prevPrice: number }
PricePoint { time: string (ISO 8601), price: number }
AnomalyEvent { id: number, marketSlug: string, detectedAt: string, eventType: string, severity: string, detail: string }
```

Member E's service layer comment: "When FastAPI is ready, replace the implementations below with fetch()."

→ `db_interface.py` must return data compatible with these shapes.

---

## Task 1: Create `core_analysis/__init__.py` + `core_analysis/db_interface.py`

**Files:**
- Create: `core_analysis/__init__.py` (empty)
- Create: `core_analysis/db_interface.py`

**Step 1: Implement db_interface.py**

```python
# core_analysis/db_interface.py
"""
Shared database interface for all PolyWatch modules.
Other members (C, D, E) import from this module to query prices,
write anomalies, and check data quality.
"""
import os
import json
from datetime import datetime, timezone, timedelta

import psycopg2
import psycopg2.extras
import pandas as pd

DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql://polywatch:polywatch@localhost:5433/polywatch",
)


def get_connection():
    return psycopg2.connect(DATABASE_URL)


# ── Price Data (for Member C algorithms) ──────────────────────────────

def get_price_series(slug: str, since: str = None) -> pd.DataFrame:
    """
    Get price history for a market slug.

    Args:
        slug: Market slug (e.g. "presidential-election-winner-2024")
        since: Optional ISO date string to filter from (e.g. "2024-10-01")

    Returns:
        DataFrame with index=time (DatetimeTZ), column=price (float)
        Matches frontend PricePoint shape: {time: ISO8601, price: 0-1}
    """
    conn = get_connection()
    where = "m.slug = %s"
    params = [slug]
    if since:
        where += " AND ph.time >= %s"
        params.append(since)

    query = f"""
        SELECT ph.time, ph.price::float AS price
        FROM price_history ph
        JOIN markets m USING (token_id)
        WHERE {where}
        ORDER BY ph.time
    """
    df = pd.read_sql(query, conn, params=params,
                     index_col="time", parse_dates=["time"])
    conn.close()
    return df


def get_markets_df() -> pd.DataFrame:
    """
    Get all markets with latest and previous price for frontend Market type.
    Returns DataFrame with columns: slug, question, active, lastPrice, prevPrice
    """
    conn = get_connection()
    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute("""
            WITH latest AS (
                SELECT DISTINCT ON (token_id)
                    token_id, time AS latest_time, price AS last_price
                FROM price_history
                ORDER BY token_id, time DESC
            ),
            previous AS (
                SELECT DISTINCT ON (token_id)
                    token_id, time AS prev_time, price AS prev_price
                FROM price_history
                WHERE time < (SELECT MAX(time) FROM price_history) - INTERVAL '24 hours'
                ORDER BY token_id, time DESC
            )
            SELECT
                m.slug,
                m.question,
                m.active,
                COALESCE(l.last_price, 0)::float AS last_price,
                COALESCE(p.prev_price, l.last_price, 0)::float AS prev_price
            FROM markets m
            LEFT JOIN latest l ON m.token_id = l.token_id
            LEFT JOIN previous p ON m.token_id = p.token_id
            ORDER BY l.latest_time DESC NULLS LAST
        """)
        rows = cur.fetchall()
    conn.close()
    return pd.DataFrame(rows)


# ── Market Info ────────────────────────────────────────────────────────

def get_active_slugs() -> list[str]:
    """Get slugs that have sufficient price data (>10 rows)."""
    conn = get_connection()
    with conn.cursor() as cur:
        cur.execute("""
            SELECT m.slug FROM markets m
            JOIN price_history ph USING (token_id)
            GROUP BY m.slug
            HAVING COUNT(*) > 10
        """)
        slugs = [r[0] for r in cur.fetchall()]
    conn.close()
    return slugs


def get_token_id_by_slug(slug: str) -> str | None:
    """Get token_id from slug, or None if not found."""
    conn = get_connection()
    with conn.cursor() as cur:
        cur.execute("SELECT token_id FROM markets WHERE slug = %s", (slug,))
        row = cur.fetchone()
    conn.close()
    return row[0] if row else None


def get_all_markets_meta() -> list[dict]:
    """Get all market metadata: {slug, token_id, question, active}."""
    conn = get_connection()
    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute("SELECT token_id, slug, question, active FROM markets ORDER BY slug")
        rows = cur.fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ── Anomaly Events (for Member C writes, Member E reads) ──────────────

def write_anomaly(token_id: str, detected_at: datetime,
                  event_type: str, severity: str, detail: dict) -> None:
    """Write one anomaly event to the database."""
    conn = get_connection()
    with conn.cursor() as cur:
        cur.execute("""
            INSERT INTO anomaly_events (token_id, detected_at, event_type, severity, detail)
            VALUES (%s, %s, %s, %s, %s)
        """, (token_id, detected_at, event_type, severity, json.dumps(detail)))
    conn.commit()
    conn.close()


def query_anomalies(slug: str = None, severity: str = None) -> pd.DataFrame:
    """
    Query anomaly events. Optionally filter by market slug and/or severity.

    Returns DataFrame with columns matching frontend AnomalyEvent type:
        id, marketSlug, detectedAt, eventType, severity, detail
    """
    conn = get_connection()
    conditions = []
    params = []
    if slug:
        conditions.append("m.slug = %s")
        params.append(slug)
    if severity:
        conditions.append("a.severity = %s")
        params.append(severity)
    where = " AND ".join(conditions)
    if where:
        where = "WHERE " + where

    query = f"""
        SELECT
            a.id,
            m.slug AS "marketSlug",
            a.detected_at AS "detectedAt",
            a.event_type AS "eventType",
            a.severity,
            a.detail
        FROM anomaly_events a
        JOIN markets m USING (token_id)
        {where}
        ORDER BY a.detected_at DESC
    """
    df = pd.read_sql(query, conn, params=params)
    conn.close()
    return df


# ── Data Quality Helpers ──────────────────────────────────────────────

def get_market_stats(slug: str = None) -> list[dict]:
    """
    Per-market statistics: row_count, time range, avg price, completeness.
    Used by data_quality.py and report generation.
    """
    conn = get_connection()
    slug_filter = "AND m.slug = %s" if slug else ""
    params = [slug] if slug else []
    query = f"""
        SELECT
            m.slug,
            m.question,
            COUNT(ph.*) AS row_count,
            MIN(ph.time) AS first_time,
            MAX(ph.time) AS last_time,
            ROUND(AVG(ph.price)::numeric, 4) AS avg_price
        FROM markets m
        LEFT JOIN price_history ph USING (token_id)
        WHERE 1=1 {slug_filter}
        GROUP BY m.slug, m.question
        ORDER BY row_count DESC
    """
    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute(query, params)
        rows = cur.fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_data_gaps(slug: str, expected_interval_hours: int = 1) -> list[dict]:
    """
    Find time gaps in price history exceeding expected interval.
    Returns list of {gap_start, gap_end, gap_hours} dicts.
    """
    df = get_price_series(slug)
    if df.empty or len(df) < 2:
        return []

    diffs = df.index.to_series().diff()
    threshold = timedelta(hours=expected_interval_hours)
    gaps_mask = diffs > threshold

    gaps = []
    for idx in df.index[gaps_mask]:
        pos = df.index.get_loc(idx)
        gap_start = df.index[pos - 1]
        gap_end = idx
        gap_hours = (gap_end - gap_start).total_seconds() / 3600
        gaps.append({
            "gap_start": gap_start.isoformat(),
            "gap_end": gap_end.isoformat(),
            "gap_hours": round(gap_hours, 1),
        })
    return gaps


def get_price_count(slug: str) -> int:
    """Get total row count for a market."""
    conn = get_connection()
    with conn.cursor() as cur:
        cur.execute("""
            SELECT COUNT(*) FROM price_history ph
            JOIN markets m USING (token_id)
            WHERE m.slug = %s
        """, (slug,))
        count = cur.fetchone()[0]
    conn.close()
    return count
```

**Step 2: Run existing tests to verify nothing breaks**

```bash
cd PolyWatch
DATABASE_URL=postgresql://polywatch:polywatch@localhost:5433/polywatch pytest tests/data_pipeline/ -v
```

Expected: 13/13 pass (existing tests unaffected)

**Step 3: Commit**

```bash
git add core_analysis/__init__.py core_analysis/db_interface.py
git commit -m "feat(core): add shared db_interface for team data access"
```

---

## Task 2: Create `core_analysis/data_quality.py`

**Files:**
- Create: `core_analysis/data_quality.py`

**Step 1: Implement**

```python
# core_analysis/data_quality.py
"""
Data Quality Report generator for PolyWatch pipeline.
Analyzes completeness, consistency, and timeliness of price data.
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'core_analysis'))

from datetime import datetime, timezone, timedelta
import pandas as pd
import numpy as np

from db_interface import get_market_stats, get_price_series, get_data_gaps, get_all_markets_meta


# Health thresholds
COMPLETENESS_HEALTHY = 95.0     # >= 95% = healthy
COMPLETENESS_DEGRADED = 85.0    # >= 85% = degraded, else critical
LATEST_AGE_HEALTHY = 2          # hours, for active markets
LATEST_AGE_DEGRADED = 12        # hours
OUT_OF_RANGE_THRESHOLD = 0      # any out-of-range is critical


def analyze_market(slug: str, question: str, row_count: int,
                   first_time, last_time, avg_price) -> dict:
    """Analyze a single market's data quality."""
    result = {
        "slug": slug,
        "question": question,
        "row_count": row_count,
        "time_range": {
            "start": first_time.isoformat() if first_time else None,
            "end": last_time.isoformat() if last_time else None,
        },
        "avg_price": float(avg_price) if avg_price else None,
        "completeness_pct": 0.0,
        "max_gap_hours": 0,
        "out_of_range_prices": 0,
        "latest_age_hours": None,
        "health": "unknown",
        "notes": [],
    }

    if row_count == 0:
        result["health"] = "no_data"
        result["notes"].append("No price data in database")
        return result

    # ── Completeness ──
    if first_time and last_time:
        span_hours = (last_time - first_time).total_seconds() / 3600
        if span_hours > 0:
            expected_points = max(span_hours, 1)  # ~1 point per hour
            completeness = min(row_count / expected_points * 100, 100.0)
            result["completeness_pct"] = round(completeness, 1)
        else:
            result["completeness_pct"] = 100.0

    # ── Data gaps ──
    try:
        gaps = get_data_gaps(slug)
        if gaps:
            result["max_gap_hours"] = max(g["gap_hours"] for g in gaps)
            result["notes"].append(f"{len(gaps)} gap(s) found, max {result['max_gap_hours']}h")
    except Exception:
        pass

    # ── Out-of-range prices ──
    try:
        df = get_price_series(slug)
        if not df.empty:
            oor = ((df['price'] < 0.0) | (df['price'] > 1.0)).sum()
            result["out_of_range_prices"] = int(oor)
            if oor > 0:
                result["notes"].append(f"{oor} price(s) outside [0.0, 1.0]")
    except Exception:
        pass

    # ── Latest age (how old is the most recent data point?) ──
    if last_time:
        now = datetime.now(timezone.utc)
        if last_time.tzinfo is None:
            last_time = last_time.replace(tzinfo=timezone.utc)
        age_hours = (now - last_time).total_seconds() / 3600
        result["latest_age_hours"] = round(age_hours, 1)

    # ── Health classification ──
    # Check if market is closed (no data expected)
    if result["latest_age_hours"] and result["latest_age_hours"] > 90 * 24:  # 90 days
        result["health"] = "closed"
        result["notes"].append("Market appears closed (no data for >90 days)")
    elif result["out_of_range_prices"] > OUT_OF_RANGE_THRESHOLD:
        result["health"] = "critical"
        result["notes"].append("Contains out-of-range price values")
    elif result["completeness_pct"] < COMPLETENESS_DEGRADED:
        result["health"] = "critical"
        result["notes"].append(f"Completeness {result['completeness_pct']}% below {COMPLETENESS_DEGRADED}%")
    elif result["completeness_pct"] < COMPLETENESS_HEALTHY:
        result["health"] = "degraded"
        result["notes"].append(f"Completeness {result['completeness_pct']}% below {COMPLETENESS_HEALTHY}%")
    elif (result["latest_age_hours"] is not None
          and result["latest_age_hours"] > LATEST_AGE_DEGRADED):
        result["health"] = "degraded"
        result["notes"].append(f"Latest data is {result['latest_age_hours']}h old")
    else:
        result["health"] = "healthy"

    if not result["notes"]:
        result["notes"].append("OK")

    return result


def generate_report() -> dict:
    """Generate complete data quality report."""
    stats = get_market_stats()
    all_meta = get_all_markets_meta()
    meta_slugs = {m["slug"] for m in all_meta}
    stat_slugs = {s["slug"] for s in stats if s["row_count"] > 0}

    # Find orphan markets (metadata but no price data)
    orphan_slugs = meta_slugs - stat_slugs
    orphan_markets = [m for m in all_meta if m["slug"] in orphan_slugs]

    # Analyze each market with data
    market_results = []
    for s in stats:
        market_results.append(analyze_market(
            slug=s["slug"],
            question=s["question"] or "",
            row_count=s["row_count"],
            first_time=s["first_time"],
            last_time=s["last_time"],
            avg_price=s["avg_price"],
        ))

    total_rows = sum(s["row_count"] for s in stats)
    active_markets = sum(1 for r in market_results if r["health"] in ("healthy", "degraded"))

    # Overall health
    healths = [r["health"] for r in market_results]
    if any(h == "critical" for h in healths):
        overall = "critical"
    elif any(h == "degraded" for h in healths):
        overall = "degraded"
    else:
        overall = "healthy"

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "summary": {
            "total_markets": len(market_results),
            "active_markets": active_markets,
            "total_rows": total_rows,
            "orphan_markets": len(orphan_markets),
            "overall_health": overall,
        },
        "markets": market_results,
        "orphan_markets": [
            {"slug": m["slug"], "question": m["question"]} for m in orphan_markets
        ],
    }


def format_markdown(report: dict) -> str:
    """Format report as human-readable markdown."""
    s = report["summary"]
    now = report["generated_at"][:10]

    health_icon = {"healthy": "HEALTHY", "degraded": "DEGRADED", "critical": "CRITICAL"}

    lines = [
        f"# PolyWatch Data Quality Report",
        f"",
        f"**Date:** {now}  ",
        f"**Health:** {health_icon.get(s['overall_health'], s['overall_health'])}  ",
        f"**Total Rows:** {s['total_rows']:,}  ",
        f"**Markets:** {s['total_markets']} ({s['active_markets']} with data)  ",
        f"**Orphan Markets:** {s['orphan_markets']} (metadata only, no price data)",
        f"",
        f"## Market Details",
        f"",
        f"| Market | Rows | Completeness | Max Gap | Health |",
        f"|--------|------|-------------|---------|--------|",
    ]

    for m in report["markets"]:
        slug = m["slug"][:40]
        rows = f"{m['row_count']:,}"
        comp = f"{m['completeness_pct']:.1f}%"
        gap = f"{m['max_gap_hours']:.0f}h" if m["max_gap_hours"] > 0 else "-"
        h = m["health"]
        lines.append(f"| {slug} | {rows} | {comp} | {gap} | {h} |")

    if report["orphan_markets"]:
        lines.append("")
        lines.append("## Orphan Markets (no price data)")
        lines.append("")
        for o in report["orphan_markets"]:
            lines.append(f"- `{o['slug']}` — {o['question']}")

    lines.append("")
    lines.append("---")
    lines.append(f"*Generated by PolyWatch data_quality.py*")
    return "\n".join(lines)
```

**Step 2: Commit**

```bash
git add core_analysis/data_quality.py
git commit -m "feat(core): add data quality analysis module"
```

---

## Task 3: Create `core_analysis/run_quality_report.py` (CLI)

**Step 1: Implement**

```python
#!/usr/bin/env python3
"""PolyWatch Data Quality Report CLI."""
import argparse
import json
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))
from data_quality import generate_report, format_markdown


def main():
    parser = argparse.ArgumentParser(description="Generate PolyWatch data quality report")
    parser.add_argument("--output", "-o", type=str, help="Output file path (default: stdout)")
    parser.add_argument("--format", "-f", type=str, choices=["markdown", "json"],
                        default="markdown", help="Output format")
    args = parser.parse_args()

    report = generate_report()

    if args.format == "json":
        text = json.dumps(report, indent=2, default=str)
    else:
        text = format_markdown(report)

    if args.output:
        with open(args.output, "w") as f:
            f.write(text)
        print(f"Report written to {args.output}")
    else:
        print(text)


if __name__ == "__main__":
    main()
```

**Step 2: Commit**

```bash
git add core_analysis/run_quality_report.py
git commit -m "feat(core): add CLI quality report generator"
```

---

## Task 4: Tests

**Files:**
- Create: `tests/core_analysis/__init__.py` (empty)
- Create: `tests/core_analysis/test_db_interface.py`
- Create: `tests/core_analysis/test_data_quality.py`
- Create: `tests/core_analysis/test_e2e.py`

**Test Plan (15 tests):**

| # | Test | Type | What it verifies |
|---|------|------|-----------------|
| 1 | `test_get_price_series_returns_df` | mock | Returns DataFrame with 'price' column |
| 2 | `test_get_price_series_since_filter` | mock | Applies `since` filter correctly |
| 3 | `test_get_active_slugs` | mock | Returns list of strings |
| 4 | `test_get_token_id_by_slug` | mock | Returns token_id or None |
| 5 | `test_get_token_id_by_slug_not_found` | mock | Returns None for missing slug |
| 6 | `test_write_anomaly_calls_sql` | mock | Executes correct INSERT SQL |
| 7 | `test_query_anomalies_returns_df` | mock | Returns DataFrame with expected columns |
| 8 | `test_query_anomalies_with_slug_filter` | mock | Filters by slug |
| 9 | `test_get_market_stats` | mock | Returns list of dicts |
| 10 | `test_get_data_gaps` | mock | Detects time gaps > threshold |
| 11 | `test_get_data_gaps_no_gaps` | mock | Returns empty list for continuous data |
| 12 | `test_report_structure` | unit | generate_report returns dict with expected keys |
| 13 | `test_completeness_calculation` | unit | Correct % for known row counts |
| 14 | `test_format_markdown_output` | unit | Markdown contains expected headers |
| 15 | `test_e2e_full_report` | e2e | Real DB → report generates without error |

---

## Task 5: Documentation + Evidence Pack

**Files:**
- Create: `core_analysis/README.md` (中文)
- Create: `Individual-Evidence-Pack-Milestone3-LIN_Tao.md` (repo 外)

---

## Commit Summary

| # | Commit | Files |
|---|--------|-------|
| 1 | `feat(core): add shared db_interface for team data access` | `core_analysis/__init__.py`, `core_analysis/db_interface.py` |
| 2 | `feat(core): add data quality analysis module` | `core_analysis/data_quality.py` |
| 3 | `feat(core): add CLI quality report generator` | `core_analysis/run_quality_report.py` |
| 4 | `test(core): add 15 tests for db_interface and data_quality` | `tests/core_analysis/` |
| 5 | `docs(core): add README and M3 evidence pack` | `core_analysis/README.md`, Evidence Pack |

## Post-M3 Impact for Other Members

| Member | How they use db_interface |
|--------|--------------------------|
| C (algorithms) | `get_price_series(slug)` → run Z-Score/Whale → `write_anomaly()` |
| D (forensics) | Replace CSV reads with `get_price_series()` |
| E (frontend) | FastAPI wraps `get_markets_df()`, `get_price_series()`, `query_anomalies()` → matches frontend contract |
