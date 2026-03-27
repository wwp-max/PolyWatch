# tests/core_analysis/test_db_interface.py
"""Unit tests for core_analysis/db_interface (mocked DB)."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../core_analysis"))

import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime, timezone
import pandas as pd

import db_interface


@pytest.fixture
def mock_conn():
    conn = MagicMock()
    cur = MagicMock()
    conn.cursor.return_value.__enter__ = MagicMock(return_value=cur)
    conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
    return conn


class TestGetPriceSeries:
    @patch.object(db_interface, "psycopg2")
    @patch.object(db_interface, "pd")
    def test_returns_dataframe(self, mock_pd, mock_psycopg2):
        mock_pd.read_sql.return_value = pd.DataFrame({"price": [0.52, 0.53]})
        result = db_interface.get_price_series("test-slug")
        assert len(result) == 2
        mock_psycopg2.connect.assert_called_once()

    @patch.object(db_interface, "psycopg2")
    @patch.object(db_interface, "pd")
    def test_since_filter(self, mock_pd, mock_psycopg2):
        mock_pd.read_sql.return_value = pd.DataFrame()
        db_interface.get_price_series("test-slug", since="2024-10-01")
        query = mock_pd.read_sql.call_args[0][0]
        assert "AND ph.time >= %s" in query


class TestGetActiveSlugs:
    @patch.object(db_interface, "psycopg2")
    def test_returns_list(self, mock_psycopg2, mock_conn):
        mock_psycopg2.connect.return_value = mock_conn
        mock_conn.cursor().__enter__().fetchall.return_value = [("s1",), ("s2",)]
        result = db_interface.get_active_slugs()
        assert result == ["s1", "s2"]


class TestGetTokenIdBySlug:
    @patch.object(db_interface, "psycopg2")
    def test_found(self, mock_psycopg2, mock_conn):
        mock_psycopg2.connect.return_value = mock_conn
        mock_conn.cursor().__enter__().fetchone.return_value = ("abc123",)
        assert db_interface.get_token_id_by_slug("slug") == "abc123"

    @patch.object(db_interface, "psycopg2")
    def test_not_found(self, mock_psycopg2, mock_conn):
        mock_psycopg2.connect.return_value = mock_conn
        mock_conn.cursor().__enter__().fetchone.return_value = None
        assert db_interface.get_token_id_by_slug("missing") is None


class TestWriteAnomaly:
    @patch.object(db_interface, "psycopg2")
    def test_insert_sql(self, mock_psycopg2, mock_conn):
        mock_psycopg2.connect.return_value = mock_conn
        db_interface.write_anomaly(
            "tok_123", datetime(2024, 1, 1, tzinfo=timezone.utc),
            "zscore_spike", "high", {"z_score": 4.2}
        )
        mock_conn.cursor().__enter__().execute.assert_called_once()
        sql = mock_conn.cursor().__enter__().execute.call_args[0][0]
        assert "INSERT INTO anomaly_events" in sql
        mock_conn.commit.assert_called_once()


class TestQueryAnomalies:
    @patch.object(db_interface, "psycopg2")
    @patch.object(db_interface, "pd")
    def test_returns_df(self, mock_pd, mock_psycopg2):
        mock_pd.read_sql.return_value = pd.DataFrame({"id": [1], "marketSlug": ["s"]})
        result = db_interface.query_anomalies()
        assert len(result) == 1
        assert "marketSlug" in result.columns

    @patch.object(db_interface, "psycopg2")
    @patch.object(db_interface, "pd")
    def test_slug_filter(self, mock_pd, mock_psycopg2):
        mock_pd.read_sql.return_value = pd.DataFrame()
        db_interface.query_anomalies(slug="test-slug")
        query = mock_pd.read_sql.call_args[0][0]
        kwargs = mock_pd.read_sql.call_args[1]
        assert "m.slug = %s" in query
        assert kwargs.get("params") == ["test-slug"]


class TestGetMarketStats:
    @patch.object(db_interface, "psycopg2")
    def test_returns_dicts(self, mock_psycopg2, mock_conn):
        mock_psycopg2.connect.return_value = mock_conn
        mock_conn.cursor().__enter__().fetchall.return_value = [
            {"slug": "s1", "question": "q", "row_count": 100,
             "first_time": None, "last_time": None, "avg_price": 0.5}
        ]
        result = db_interface.get_market_stats()
        assert len(result) == 1
        assert result[0]["slug"] == "s1"


class TestGetDataGaps:
    @patch.object(db_interface, "get_price_series")
    def test_detects_gap(self, mock_get):
        idx = pd.to_datetime([
            "2024-01-01 00:00", "2024-01-01 01:00", "2024-01-01 02:00",
            "2024-01-03 00:00", "2024-01-03 01:00",
        ]).tz_localize("UTC")
        mock_get.return_value = pd.DataFrame({"price": [0.5]*5}, index=idx)
        gaps = db_interface.get_data_gaps("test-slug")
        assert len(gaps) == 1
        assert gaps[0]["gap_hours"] == 46.0

    @patch.object(db_interface, "get_price_series")
    def test_no_gaps(self, mock_get):
        idx = pd.date_range("2024-01-01", periods=10, freq="h", tz="UTC")
        mock_get.return_value = pd.DataFrame({"price": [0.5]*10}, index=idx)
        assert len(db_interface.get_data_gaps("test-slug")) == 0

    @patch.object(db_interface, "get_price_series")
    def test_empty_series(self, mock_get):
        mock_get.return_value = pd.DataFrame(columns=["price"])
        assert len(db_interface.get_data_gaps("test-slug")) == 0
