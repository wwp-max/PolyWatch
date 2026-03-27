# tests/core_analysis/test_e2e.py
"""End-to-end integration tests against live TimescaleDB."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../core_analysis"))

import pytest
from datetime import datetime, timezone

import db_interface
import data_quality


DB_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql://polywatch:polywatch@localhost:5433/polywatch",
)


@pytest.fixture(autouse=True)
def patch_db_url(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", DB_URL)
    monkeypatch.setattr(db_interface, "DATABASE_URL", DB_URL)


class TestDbInterfaceLive:
    def test_get_price_series_returns_data(self):
        df = db_interface.get_price_series("presidential-election-winner-2024")
        assert len(df) == 7356
        assert "price" in df.columns
        assert 0.0 <= df["price"].min() <= 1.0

    def test_get_active_slugs(self):
        slugs = db_interface.get_active_slugs()
        assert len(slugs) >= 3
        assert "presidential-election-winner-2024" in slugs

    def test_write_and_query_anomaly(self):
        token_id = db_interface.get_token_id_by_slug("presidential-election-winner-2024")
        db_interface.write_anomaly(
            token_id,
            datetime(2024, 6, 1, 12, 0, 0, tzinfo=timezone.utc),
            "zscore_spike", "high", {"z_score": 5.0, "test": True}
        )
        df = db_interface.query_anomalies(slug="presidential-election-winner-2024", severity="high")
        assert len(df) >= 1
        assert "marketSlug" in df.columns


class TestQualityReportLive:
    def test_full_report_generates(self):
        report = data_quality.generate_report()
        assert report["summary"]["total_markets"] >= 3
        assert report["summary"]["total_rows"] >= 10000
        assert report["summary"]["overall_health"] in ("healthy", "degraded", "critical")

    def test_2024_election_completeness(self):
        stats = db_interface.get_market_stats(slug="presidential-election-winner-2024")
        s = stats[0]
        result = data_quality.analyze_market(
            slug=s["slug"], question=s["question"],
            row_count=s["row_count"], first_time=s["first_time"],
            last_time=s["last_time"], avg_price=s["avg_price"],
        )
        assert result["completeness_pct"] >= 99.0
        assert result["out_of_range_prices"] == 0
