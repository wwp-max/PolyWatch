# data_pipeline/collector/main.py
import os
import time
import schedule
from datetime import datetime, timezone, timedelta

from fetcher import resolve_token_id, fetch_price_history
from db import get_connection, upsert_market, insert_price_rows, get_latest_timestamp

# ── Markets to monitor ──────────────────────────────────────────────────────
# Selection rationale (per project spec):
#   - 1 closed market for backtesting / algorithm training
#   - 2 active high-liquidity markets for live monitoring
TRACKED_MARKETS = [
    # Closed — used for backtesting (2024 US election, settled Nov 2024)
    "presidential-election-winner-2024",
    # Active — geopolitical (Russia-Ukraine ceasefire, price ~0.58, ends 2026-07)
    "what-will-happen-before-gta-vi",
    # Active — US policy (Trump Greenland acquisition, price ~0.11, ends 2026-12)
    "will-trump-acquire-greenland-before-2027",
]

POLL_INTERVAL = int(os.environ.get("POLL_INTERVAL_SECONDS", "300"))

# How far back to fetch if a market has never been seen before (days)
INITIAL_LOOKBACK_DAYS = 30

# CLOB API rejects requests with interval > ~7 days; chunk accordingly
FETCH_CHUNK_DAYS = 6


def collect_once():
    """Run one full collection pass across all tracked markets."""
    print(f"[collector] Starting collection pass at {datetime.now(timezone.utc).isoformat()}")

    try:
        conn = get_connection()
    except Exception as e:
        print(f"[collector] DB connection failed: {e}")
        return

    try:
        for slug in TRACKED_MARKETS:
            try:
                token_id, question = resolve_token_id(slug)
                if not token_id or question is None:
                    print(f"[collector] Could not resolve slug: {slug}, skipping.")
                    continue

                upsert_market(conn, token_id, slug, question)

                latest = get_latest_timestamp(conn, token_id)
                if latest:
                    # Normalize to UTC-aware in case psycopg2 returns naive datetime
                    if latest.tzinfo is None:
                        latest = latest.replace(tzinfo=timezone.utc)
                    start_ts = int(latest.timestamp()) + 1  # +1 to avoid re-fetching last point
                else:
                    start_ts = int((datetime.now(timezone.utc) - timedelta(days=INITIAL_LOOKBACK_DAYS)).timestamp())

                end_ts = int(datetime.now(timezone.utc).timestamp())

                if start_ts >= end_ts:
                    print(f"[collector] {slug}: already up to date.")
                    continue

                # Fetch in chunks to stay within CLOB API's interval limit (~7 days)
                chunk_secs = FETCH_CHUNK_DAYS * 86400
                total_fetched = 0
                total_inserted = 0
                cursor = start_ts
                while cursor < end_ts:
                    chunk_end = min(cursor + chunk_secs, end_ts)
                    rows = fetch_price_history(token_id, cursor, chunk_end)
                    if rows:
                        inserted = insert_price_rows(conn, token_id, rows)
                        total_fetched += len(rows)
                        total_inserted += inserted
                    cursor = chunk_end + 1

                print(f"[collector] {slug}: fetched {total_fetched} points, inserted {total_inserted} new rows.")

            except Exception as e:
                print(f"[collector] Error processing {slug}: {e}")
    finally:
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
