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

                rows = fetch_price_history(token_id, start_ts, end_ts)
                inserted = insert_price_rows(conn, token_id, rows)
                print(f"[collector] {slug}: fetched {len(rows)} points, inserted {inserted} new rows.")

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
