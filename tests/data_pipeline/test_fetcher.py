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
