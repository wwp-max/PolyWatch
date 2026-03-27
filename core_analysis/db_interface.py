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
        Matches frontend PricePoint type: {time: ISO8601, price: 0-1}
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
    Get all markets with latest and previous price.
    Returns DataFrame with columns: slug, question, active, last_price, prev_price.
    Matches frontend Market type: {slug, question, active, lastPrice, prevPrice}
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
                SELECT DISTINCT ON (ph.token_id)
                    ph.token_id, ph.price AS prev_price
                FROM price_history ph
                JOIN markets m ON ph.token_id = m.token_id
                JOIN latest l ON ph.token_id = l.token_id
                WHERE ph.time < l.latest_time - INTERVAL '24 hours'
                ORDER BY ph.token_id, ph.time DESC
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
    Per-market statistics: row_count, time range, avg price.
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
