# tests/core_analysis/test_data_quality.py
"""Unit tests for core_analysis/data_quality.py (mocked db_interface)."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../core_analysis"))

import pytest
from unittest.mock import patch
from datetime import datetime, timezone, timedelta

import data_quality
from data_quality import analyze_market, generate_report, format_markdown


class TestAnalyzeMarket:
    @patch.object(data_quality, "get_data_gaps", return_value=[])
    @patch.object(data_quality, "get_price_series")
    def test_healthy_market(self, mock_ps, mock_gaps):
        mock_ps.return_value = __import__("pandas").DataFrame(
            {"price": [0.55] * 720},
            index=__import__("pandas").date_range("2026-02-01", periods=720, freq="h", tz="UTC")
        )
        now = datetime.now(timezone.utc)
        start = now - timedelta(days=30)
        result = analyze_market(
            slug="test-slug", question="Test?",
            row_count=720, first_time=start, last_time=now, avg_price=0.55
        )
        assert result["slug"] == "test-slug"
        assert result["row_count"] == 720
        assert result["health"] == "healthy"

    def test_no_data_market(self):
        result = analyze_market(
            slug="empty-slug", question="Empty",
            row_count=0, first_time=None, last_time=None, avg_price=None
        )
        assert result["health"] == "no_data"
        assert "No price data" in result["notes"][0]

    @patch.object(data_quality, "get_data_gaps", return_value=[])
    @patch.object(data_quality, "get_price_series")
    def test_closed_market(self, mock_ps, mock_gaps):
        mock_ps.return_value = __import__("pandas").DataFrame(columns=["price"])
        old = datetime(2024, 1, 1, tzinfo=timezone.utc)
        result = analyze_market(
            slug="closed-slug", question="Closed",
            row_count=500, first_time=old, last_time=old + timedelta(days=30),
            avg_price=0.5
        )
        assert result["health"] == "closed"

    @patch.object(data_quality, "get_data_gaps")
    @patch.object(data_quality, "get_price_series")
    def test_gap_notes(self, mock_ps, mock_gaps):
        mock_ps.return_value = __import__("pandas").DataFrame(
            {"price": [0.5]}, index=__import__("pandas").date_range("2026-01-01", periods=1, freq="h", tz="UTC")
        )
        mock_gaps.return_value = [
            {"gap_start": "x", "gap_end": "y", "gap_hours": 48.0}
        ]
        now = datetime.now(timezone.utc)
        start = now - timedelta(days=10)
        result = analyze_market(
            slug="gap-slug", question="Gaps",
            row_count=200, first_time=start, last_time=now, avg_price=0.5
        )
        assert result["max_gap_hours"] == 48.0
        assert any("gap" in n.lower() for n in result["notes"])

    @patch.object(data_quality, "get_data_gaps", return_value=[])
    @patch.object(data_quality, "get_price_series")
    def test_completeness(self, mock_ps, mock_gaps):
        mock_ps.return_value = __import__("pandas").DataFrame(
            {"price": [0.5] * 7356},
            index=__import__("pandas").date_range("2024-01-05", periods=7356, freq="h", tz="UTC")
        )
        start = datetime(2024, 1, 5, tzinfo=timezone.utc)
        end = datetime(2024, 11, 6, tzinfo=timezone.utc)
        result = analyze_market(
            slug="comp-slug", question="Comp",
            row_count=7356, first_time=start, last_time=end, avg_price=0.5
        )
        assert result["completeness_pct"] >= 99.0


class TestGenerateReport:
    @patch.object(data_quality, "get_data_gaps", return_value=[])
    @patch.object(data_quality, "get_price_series")
    @patch.object(data_quality, "get_all_markets_meta")
    @patch.object(data_quality, "get_market_stats")
    def test_report_structure(self, mock_stats, mock_meta, mock_ps, mock_gaps):
        mock_ps.return_value = __import__("pandas").DataFrame(
            {"price": [0.5]}, index=__import__("pandas").date_range("2026-01-01", periods=1, freq="h", tz="UTC")
        )
        now = datetime.now(timezone.utc)
        mock_stats.return_value = [
            {"slug": "s1", "question": "Q1", "row_count": 7000,
             "first_time": now - timedelta(days=30), "last_time": now, "avg_price": 0.5},
            {"slug": "s2", "question": "Q2", "row_count": 0,
             "first_time": None, "last_time": None, "avg_price": None},
        ]
        mock_meta.return_value = [
            {"slug": "s1", "token_id": "t1", "question": "Q1", "active": True},
            {"slug": "s2", "token_id": "t2", "question": "Q2", "active": False},
        ]
        report = generate_report()
        assert "generated_at" in report
        assert "summary" in report
        assert report["summary"]["total_markets"] == 2

    @patch.object(data_quality, "get_data_gaps", return_value=[])
    @patch.object(data_quality, "get_price_series")
    @patch.object(data_quality, "get_all_markets_meta")
    @patch.object(data_quality, "get_market_stats")
    def test_orphan_detection(self, mock_stats, mock_meta, mock_ps, mock_gaps):
        mock_ps.return_value = __import__("pandas").DataFrame(columns=["price"])
        mock_stats.return_value = [
            {"slug": "s1", "question": "Q1", "row_count": 100,
             "first_time": None, "last_time": None, "avg_price": 0.5}
        ]
        mock_meta.return_value = [
            {"slug": "s1", "token_id": "t1", "question": "Q1", "active": True},
            {"slug": "s2", "token_id": "t2", "question": "Q2", "active": False},
        ]
        report = generate_report()
        assert report["summary"]["orphan_markets"] == 1
        assert report["orphan_markets"][0]["slug"] == "s2"


class TestFormatMarkdown:
    def test_contains_headers(self):
        report = {
            "generated_at": "2026-03-08T12:00:00+00:00",
            "summary": {"total_markets": 1, "active_markets": 1,
                         "total_rows": 1000, "orphan_markets": 0,
                         "overall_health": "healthy"},
            "markets": [
                {"slug": "test", "question": "Q", "row_count": 1000,
                 "completeness_pct": 99.0, "max_gap_hours": 0,
                 "out_of_range_prices": 0, "latest_age_hours": 1.0,
                 "health": "healthy", "notes": ["OK"],
                 "time_range": {"start": "x", "end": "y"}, "avg_price": 0.5},
            ],
            "orphan_markets": [],
        }
        md = format_markdown(report)
        assert "# PolyWatch Data Quality Report" in md
        assert "HEALTHY" in md
        assert "1,000" in md
        assert "test" in md
