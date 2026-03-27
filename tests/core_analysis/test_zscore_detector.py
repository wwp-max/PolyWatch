# tests/core_analysis/test_zscore_detector.py
"""
Unit tests for Z-Score / Moving Average anomaly detector.
Uses synthetic data only — no database required.
"""
import pytest
import pandas as pd
import numpy as np

from core_analysis.zscore_detector import (
    ZScoreDetector, ZScoreConfig, run_zscore_analysis, _safe_float,
)


# ── Fixtures ───────────────────────────────────────────────────────

@pytest.fixture
def stable_prices():
    """Stable price series with low volatility (no anomalies expected)."""
    np.random.seed(1)
    idx = pd.date_range("2024-01-01", periods=200, freq="h", tz="UTC")
    prices = pd.Series(0.50 + np.random.normal(0, 0.002, 200), index=idx)
    return prices.clip(0, 1)


@pytest.fixture
def prices_with_spike():
    """Price series with clear anomalous spikes injected."""
    np.random.seed(2)
    idx = pd.date_range("2024-01-01", periods=300, freq="h", tz="UTC")
    prices = pd.Series(0.50 + np.cumsum(np.random.normal(0, 0.002, 300)), index=idx)
    prices = prices.clip(0.1, 0.9)
    # Inject clear spikes
    prices.iloc[100] += 0.20  # big spike up
    prices.iloc[200] -= 0.18  # big spike down
    return prices


@pytest.fixture
def detector():
    return ZScoreDetector()


# ── Tests ──────────────────────────────────────────────────────────

class TestZScoreDetector:

    def test_detect_returns_dataframe(self, detector, stable_prices):
        result = detector.detect(stable_prices)
        assert isinstance(result, pd.DataFrame)
        assert "price" in result.columns
        assert "z_short" in result.columns
        assert "z_medium" in result.columns
        assert "z_long" in result.columns
        assert "z_ewma" in result.columns
        assert "is_anomaly" in result.columns
        assert "severity" in result.columns

    def test_detect_same_length_as_input(self, detector, stable_prices):
        result = detector.detect(stable_prices)
        assert len(result) == len(stable_prices)

    def test_stable_prices_few_anomalies(self, detector, stable_prices):
        result = detector.detect(stable_prices)
        anomalies = detector.get_anomalies(result)
        # Stable data should produce very few anomalies
        assert len(anomalies) < len(stable_prices) * 0.10

    def test_spike_detected(self, detector, prices_with_spike):
        result = detector.detect(prices_with_spike)
        anomalies = detector.get_anomalies(result)
        assert len(anomalies) > 0, "Should detect at least one anomaly from injected spikes"

    def test_spike_severity(self, prices_with_spike):
        config = ZScoreConfig(z_threshold=2.0, high_severity_z=3.5)
        detector = ZScoreDetector(config)
        result = detector.detect(prices_with_spike)
        anomalies = detector.get_anomalies(result)
        # At least one should be high severity given the large spike
        severities = anomalies["severity"].unique()
        assert "high" in severities or "medium" in severities

    def test_custom_threshold(self, prices_with_spike):
        # Very high threshold should detect fewer anomalies
        strict = ZScoreDetector(ZScoreConfig(z_threshold=5.0, return_spike_threshold=0.50))
        loose = ZScoreDetector(ZScoreConfig(z_threshold=1.5, return_spike_threshold=0.01))

        strict_result = strict.detect(prices_with_spike)
        loose_result = loose.detect(prices_with_spike)

        strict_count = strict.get_anomalies(strict_result).shape[0]
        loose_count = loose.get_anomalies(loose_result).shape[0]
        assert loose_count >= strict_count

    def test_get_anomaly_events(self, detector, prices_with_spike):
        result = detector.detect(prices_with_spike)
        events = detector.get_anomaly_events(result, market_slug="test-market")
        assert isinstance(events, list)
        if len(events) > 0:
            event = events[0]
            assert "detected_at" in event
            assert "event_type" in event
            assert event["event_type"] == "zscore_spike"
            assert "severity" in event
            assert "detail" in event
            assert event["detail"]["market_slug"] == "test-market"

    def test_cluster_anomalies(self, detector, prices_with_spike):
        result = detector.detect(prices_with_spike)
        clusters = detector.cluster_anomalies(result)
        assert isinstance(clusters, list)
        if len(clusters) > 0:
            c = clusters[0]
            assert "start" in c
            assert "end" in c
            assert "peak_z" in c
            assert "count" in c

    def test_summary(self, detector, prices_with_spike):
        result = detector.detect(prices_with_spike)
        summary = detector.summary(result)
        assert "total_points" in summary
        assert "anomaly_points" in summary
        assert "anomaly_rate" in summary
        assert "clusters" in summary
        assert summary["total_points"] > 0

    def test_empty_series(self, detector):
        empty = pd.Series(dtype=float, index=pd.DatetimeIndex([], tz="UTC"))
        result = detector.detect(empty)
        assert len(result) == 0

    def test_short_series(self, detector):
        idx = pd.date_range("2024-01-01", periods=5, freq="h", tz="UTC")
        prices = pd.Series([0.5, 0.51, 0.49, 0.50, 0.52], index=idx)
        result = detector.detect(prices)
        assert len(result) == 5


class TestRunZscoreAnalysis:

    def test_returns_all_keys(self, stable_prices):
        result = run_zscore_analysis(stable_prices)
        assert "result_df" in result
        assert "anomalies_df" in result
        assert "events" in result
        assert "clusters" in result
        assert "summary" in result


class TestSafeFloat:

    def test_normal_float(self):
        assert _safe_float(3.14) == 3.14

    def test_nan(self):
        assert _safe_float(float("nan")) is None

    def test_none(self):
        assert _safe_float(None) is None

    def test_numpy_nan(self):
        assert _safe_float(np.nan) is None

    def test_integer(self):
        assert _safe_float(42) == 42.0
