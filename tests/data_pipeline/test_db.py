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
        from db import upsert_market
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
        assert latest.astimezone(timezone.utc) == datetime(2024, 11, 1, 2, 0, tzinfo=timezone.utc)
