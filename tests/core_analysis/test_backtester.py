# tests/core_analysis/test_backtester.py
"""
Unit tests for the backtesting framework.
Uses synthetic data only — no database required.
"""
import pytest
import pandas as pd
import numpy as np
from datetime import timedelta

from core_analysis.backtester import (
    Backtester, LabelConfig,
    generate_ground_truth, compute_metrics,
    ELECTION_EVENTS,
)
from core_analysis.zscore_detector import ZScoreConfig
from core_analysis.benford_detector import BenfordConfig
from core_analysis.whale_alert import WhaleConfig


# ── Fixtures ───────────────────────────────────────────────────────

@pytest.fixture
def synthetic_election_prices():
    """
    Synthetic price series mimicking 2024 election with known event effects.
    """
    np.random.seed(42)
    # ~300 days of hourly data covering election period
    n_points = 7200  # 300 days
    idx = pd.date_range("2024-01-05", periods=n_points, freq="h", tz="UTC")
    base = 0.50 + np.cumsum(np.random.normal(0, 0.0005, n_points))

    prices = pd.Series(base, index=idx).clip(0.05, 0.95)

    # Inject known event effects
    event_effects = {
        "2024-01-15": 0.04,
        "2024-03-05": 0.03,
        "2024-06-27": 0.08,
        "2024-07-13": 0.06,
        "2024-07-21": -0.10,
        "2024-08-22": -0.05,
        "2024-09-10": -0.03,
    }
    for date_str, effect in event_effects.items():
        event_time = pd.Timestamp(date_str, tz="UTC")
        mask = (prices.index >= event_time) & (
            prices.index < event_time + timedelta(hours=6)
        )
        prices[mask] += effect

    return prices.clip(0.05, 0.95)


@pytest.fixture
def short_prices():
    """Short price series for quick tests."""
    np.random.seed(50)
    idx = pd.date_range("2024-06-01", periods=500, freq="h", tz="UTC")
    prices = pd.Series(0.50 + np.cumsum(np.random.normal(0, 0.003, 500)), index=idx)
    # Inject one spike
    prices.iloc[200] += 0.15
    return prices.clip(0.05, 0.95)


@pytest.fixture
def backtester(synthetic_election_prices):
    return Backtester(synthetic_election_prices)


# ── Tests: Ground Truth ───────────────────────────────────────────

class TestGenerateGroundTruth:

    def test_output_type(self, synthetic_election_prices):
        labels = generate_ground_truth(synthetic_election_prices)
        assert isinstance(labels, pd.Series)
        assert labels.dtype == int

    def test_output_length(self, synthetic_election_prices):
        labels = generate_ground_truth(synthetic_election_prices)
        assert len(labels) == len(synthetic_election_prices)

    def test_has_positives(self, synthetic_election_prices):
        labels = generate_ground_truth(synthetic_election_prices)
        assert labels.sum() > 0, "Should have some positive labels from events"

    def test_has_negatives(self, synthetic_election_prices):
        labels = generate_ground_truth(synthetic_election_prices)
        assert (labels == 0).sum() > 0

    def test_custom_events(self, synthetic_election_prices):
        custom_events = [{"date": "2024-06-15", "name": "Test Event"}]
        labels = generate_ground_truth(
            synthetic_election_prices,
            events=custom_events,
            config=LabelConfig(price_change_threshold=1.0),  # Disable price-based
        )
        # Only one event, so positives should be limited
        assert labels.sum() > 0

    def test_price_change_labeling(self):
        idx = pd.date_range("2024-01-01", periods=100, freq="h", tz="UTC")
        prices = pd.Series([0.5] * 100, index=idx)
        prices.iloc[50] = 0.6  # 10% jump
        labels = generate_ground_truth(
            prices,
            events=[],  # No events
            config=LabelConfig(price_change_threshold=0.05),
        )
        assert labels.iloc[50] == 1


# ── Tests: Metrics ─────────────────────────────────────────────────

class TestComputeMetrics:

    def test_perfect_prediction(self):
        y_true = pd.Series([0, 0, 1, 1, 0, 1])
        y_pred = pd.Series([0, 0, 1, 1, 0, 1])
        m = compute_metrics(y_true, y_pred)
        assert m["precision"] == 1.0
        assert m["recall"] == 1.0
        assert m["f1"] == 1.0
        assert m["accuracy"] == 1.0
        assert m["FP"] == 0
        assert m["FN"] == 0

    def test_all_wrong(self):
        y_true = pd.Series([0, 0, 0, 0])
        y_pred = pd.Series([1, 1, 1, 1])
        m = compute_metrics(y_true, y_pred)
        assert m["precision"] == 0.0
        assert m["FP"] == 4

    def test_no_positives_predicted(self):
        y_true = pd.Series([1, 1, 1])
        y_pred = pd.Series([0, 0, 0])
        m = compute_metrics(y_true, y_pred)
        assert m["recall"] == 0.0
        assert m["FN"] == 3

    def test_metrics_fields(self):
        y_true = pd.Series([0, 1, 0, 1])
        y_pred = pd.Series([0, 1, 1, 0])
        m = compute_metrics(y_true, y_pred)
        expected_keys = {"TP", "FP", "TN", "FN", "precision", "recall",
                         "f1", "accuracy", "FPR", "FNR", "total",
                         "positives", "negatives"}
        assert expected_keys.issubset(m.keys())


# ── Tests: Z-Score Backtesting ─────────────────────────────────────

class TestZScoreBacktest:

    def test_evaluate_returns_metrics(self, backtester):
        metrics = backtester.evaluate_zscore()
        assert "precision" in metrics
        assert "recall" in metrics
        assert "f1" in metrics
        assert metrics["detector"] == "zscore"

    def test_custom_config(self, backtester):
        config = ZScoreConfig(z_threshold=3.0, short_window=12)
        metrics = backtester.evaluate_zscore(config=config)
        assert metrics["config"]["z_threshold"] == 3.0

    def test_grid_search(self, short_prices):
        bt = Backtester(short_prices)
        grid = bt.grid_search_zscore(
            z_thresholds=[2.0, 3.0],
            short_windows=[6],
            medium_windows=[24],
            return_spike_thresholds=[0.05],
        )
        assert isinstance(grid, pd.DataFrame)
        assert len(grid) == 2  # 2 thresholds * 1 * 1 * 1
        assert "f1" in grid.columns


# ── Tests: Benford Backtesting ─────────────────────────────────────

class TestBenfordBacktest:

    def test_evaluate_returns_metrics(self, backtester):
        metrics = backtester.evaluate_benford()
        assert "precision" in metrics
        assert metrics["detector"] == "benford"


# ── Tests: Whale Alert Backtesting ─────────────────────────────────

class TestWhaleBacktest:

    def test_evaluate_returns_metrics(self, backtester):
        metrics = backtester.evaluate_whale()
        assert "precision" in metrics
        assert metrics["detector"] == "whale_alert"


# ── Tests: Combined Evaluation ─────────────────────────────────────

class TestEvaluateAll:

    def test_returns_all_detectors(self, backtester):
        results = backtester.evaluate_all()
        assert "zscore" in results
        assert "benford" in results
        assert "whale_alert" in results
        assert "combined" in results
        assert "ground_truth_summary" in results

    def test_ground_truth_summary(self, backtester):
        results = backtester.evaluate_all()
        gt = results["ground_truth_summary"]
        assert gt["total"] > 0
        assert gt["positives"] >= 0
        assert gt["negatives"] >= 0


# ── Tests: Threshold Sweep ─────────────────────────────────────────

class TestThresholdSweep:

    def test_returns_dataframe(self, short_prices):
        bt = Backtester(short_prices)
        df = bt.threshold_sweep_zscore(thresholds=[2.0, 3.0, 4.0])
        assert isinstance(df, pd.DataFrame)
        assert "threshold" in df.columns
        assert "FPR" in df.columns
        assert "TPR" in df.columns
        assert len(df) == 3


# ── Tests: Event Detection Report ──────────────────────────────────

class TestEventReport:

    def test_returns_dataframe(self, backtester):
        report = backtester.event_detection_report()
        assert isinstance(report, pd.DataFrame)
        assert "event_name" in report.columns
        assert "detected" in report.columns
        assert len(report) == len(ELECTION_EVENTS)

    def test_detected_column_is_bool(self, backtester):
        report = backtester.event_detection_report()
        assert report["detected"].dtype == bool


# ── Tests: Election Events ─────────────────────────────────────────

class TestElectionEvents:

    def test_events_have_required_keys(self):
        for event in ELECTION_EVENTS:
            assert "date" in event
            assert "name" in event
            assert "expected_direction" in event

    def test_events_are_chronological(self):
        dates = [pd.Timestamp(e["date"]) for e in ELECTION_EVENTS]
        assert dates == sorted(dates)

    def test_at_least_5_events(self):
        assert len(ELECTION_EVENTS) >= 5
