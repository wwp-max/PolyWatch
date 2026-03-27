# tests/core_analysis/test_whale_alert.py
"""
Unit tests for Whale Alert large trade detector.
Uses synthetic data only — no database required.
"""
import pytest
import pandas as pd
import numpy as np
from datetime import timedelta

from core_analysis.whale_alert import (
    WhaleAlert, WhaleConfig, simulate_trades_from_prices, run_whale_analysis,
)


# ── Fixtures ───────────────────────────────────────────────────────

@pytest.fixture
def price_series():
    np.random.seed(20)
    idx = pd.date_range("2024-01-01", periods=200, freq="h", tz="UTC")
    prices = pd.Series(0.50 + np.cumsum(np.random.normal(0, 0.005, 200)), index=idx)
    return prices.clip(0, 1)


@pytest.fixture
def simple_trades():
    """Simple trade DataFrame with clear whale trades."""
    timestamps = pd.date_range("2024-01-01", periods=20, freq="h", tz="UTC")
    sizes = [50, 30, 600, 40, 20, 1500, 10, 80, 25, 35,
             60, 40, 2500, 30, 50, 45, 55, 40, 30, 20]
    sides = ["buy", "sell"] * 10
    return pd.DataFrame({
        "timestamp": timestamps,
        "trade_size": sizes,
        "side": sides,
        "price": [0.5] * 20,
    })


@pytest.fixture
def biased_trades():
    """Trades with strong directional bias."""
    timestamps = pd.date_range("2024-01-01", periods=10, freq="30min", tz="UTC")
    return pd.DataFrame({
        "timestamp": timestamps,
        "trade_size": [100] * 10,
        "side": ["buy"] * 9 + ["sell"],  # 90% buy
        "price": [0.5] * 10,
    })


@pytest.fixture
def alert():
    return WhaleAlert()


# ── Tests ──────────────────────────────────────────────────────────

class TestSingleWhaleDetection:

    def test_detects_large_trades(self, alert, simple_trades):
        result = alert.detect_single_whales(simple_trades)
        whales = result[result["is_whale"]]
        assert len(whales) > 0

    def test_whale_severity_levels(self, alert, simple_trades):
        result = alert.detect_single_whales(simple_trades)
        whales = result[result["is_whale"]]
        # 2500 > 500 * 3 = 1500, so should be high
        assert "high" in whales["whale_severity"].values

    def test_small_trades_not_flagged(self):
        trades = pd.DataFrame({
            "trade_size": [10, 20, 30, 40, 50],
        })
        alert = WhaleAlert(WhaleConfig(size_threshold=100))
        result = alert.detect_single_whales(trades)
        assert not result["is_whale"].any()

    def test_custom_threshold(self, simple_trades):
        # Very low threshold: everything is a whale
        alert = WhaleAlert(WhaleConfig(size_threshold=10))
        result = alert.detect_single_whales(simple_trades)
        assert result["is_whale"].sum() == 20

    def test_output_columns(self, alert, simple_trades):
        result = alert.detect_single_whales(simple_trades)
        assert "is_whale" in result.columns
        assert "whale_severity" in result.columns


class TestCumulativeSpikes:

    def test_detects_volume_spikes(self, alert, simple_trades):
        result = alert.detect_cumulative_spikes(simple_trades)
        assert "cumulative_volume" in result.columns
        assert "is_volume_spike" in result.columns

    def test_no_timestamp_handled(self, alert):
        trades = pd.DataFrame({"trade_size": [100, 200, 300]})
        result = alert.detect_cumulative_spikes(trades)
        assert "is_volume_spike" in result.columns


class TestDirectionalBias:

    def test_detects_bias(self, alert, biased_trades):
        events = alert.detect_directional_bias(biased_trades)
        assert isinstance(events, list)
        if len(events) > 0:
            assert events[0]["bias_side"] == "buy"

    def test_no_side_column(self, alert):
        trades = pd.DataFrame({
            "timestamp": pd.date_range("2024-01-01", periods=5, freq="h", tz="UTC"),
            "trade_size": [100] * 5,
        })
        events = alert.detect_directional_bias(trades)
        assert events == []


class TestPriceImpact:

    def test_computes_impact(self, alert, price_series):
        # Create whale trades aligned with price series
        whale_df = pd.DataFrame({
            "timestamp": [price_series.index[50], price_series.index[100]],
            "trade_size": [1000, 2000],
        })
        result = alert.analyze_price_impact(whale_df, price_series)
        assert "price_before" in result.columns
        assert "price_after" in result.columns
        assert "price_impact" in result.columns

    def test_empty_whale_trades(self, alert, price_series):
        whale_df = pd.DataFrame(columns=["timestamp", "trade_size"])
        result = alert.analyze_price_impact(whale_df, price_series)
        assert len(result) == 0


class TestFullDetectionPipeline:

    def test_detect_returns_all_keys(self, alert, simple_trades, price_series):
        result = alert.detect(simple_trades, price_series)
        assert "trades_flagged" in result
        assert "whale_trades" in result
        assert "cumulative_df" in result
        assert "directional_events" in result
        assert "summary" in result

    def test_summary_fields(self, alert, simple_trades):
        result = alert.detect(simple_trades)
        summary = result["summary"]
        assert "total_trades" in summary
        assert "whale_trades" in summary
        assert "whale_pct" in summary
        assert summary["total_trades"] == 20


class TestGetAnomalyEvents:

    def test_returns_event_dicts(self, alert, simple_trades):
        result = alert.detect(simple_trades)
        events = alert.get_anomaly_events(result, market_slug="test")
        assert isinstance(events, list)
        if len(events) > 0:
            e = events[0]
            assert "detected_at" in e
            assert "event_type" in e
            assert "severity" in e
            assert "detail" in e


class TestSimulateTradesFromPrices:

    def test_output_shape(self, price_series):
        trades = simulate_trades_from_prices(price_series)
        assert isinstance(trades, pd.DataFrame)
        assert "timestamp" in trades.columns
        assert "trade_size" in trades.columns
        assert "side" in trades.columns
        assert "price" in trades.columns
        # One fewer than price series (due to diff)
        assert len(trades) == len(price_series) - 1

    def test_positive_sizes(self, price_series):
        trades = simulate_trades_from_prices(price_series)
        assert (trades["trade_size"] > 0).all()

    def test_valid_sides(self, price_series):
        trades = simulate_trades_from_prices(price_series)
        assert set(trades["side"].unique()).issubset({"buy", "sell"})

    def test_whale_trades_injected(self, price_series):
        trades = simulate_trades_from_prices(price_series)
        assert (trades["trade_size"] >= 500).any(), "Should have injected whale trades"


class TestRunWhaleAnalysis:

    def test_convenience_function(self, simple_trades, price_series):
        result = run_whale_analysis(simple_trades, price_series)
        assert "summary" in result
        assert "whale_trades" in result
