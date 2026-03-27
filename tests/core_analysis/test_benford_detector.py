# tests/core_analysis/test_benford_detector.py
"""
Unit tests for Benford's Law anomaly detector.
Uses synthetic data only — no database required.
"""
import pytest
import pandas as pd
import numpy as np

from core_analysis.benford_detector import (
    BenfordDetector, BenfordConfig, BENFORD_PROBS,
    prepare_price_changes, run_benford_analysis,
)


# ── Fixtures ───────────────────────────────────────────────────────

@pytest.fixture
def benford_conforming_data():
    """Synthetic data whose first digits follow Benford's Law by construction.

    Numbers are built by sampling first digits according to Benford
    probabilities, then attaching a random magnitude and mantissa.
    This guarantees the chi-squared / MAD tests will pass.
    """
    import math
    np.random.seed(42)
    n = 5000
    benford_probs = [math.log10(1 + 1 / d) for d in range(1, 10)]
    digits = np.random.choice(range(1, 10), size=n, p=benford_probs)
    # number = first_digit * 10^(uniform magnitude) * (1 + uniform mantissa)
    data = digits * 10 ** np.random.uniform(0, 3, n) * (1 + np.random.uniform(0, 0.9, n))
    return pd.Series(data)


@pytest.fixture
def non_conforming_data():
    """Uniformly distributed data — should NOT conform to Benford's Law."""
    np.random.seed(11)
    return pd.Series(np.random.uniform(100, 999, size=500))


@pytest.fixture
def price_series():
    """Realistic price series for testing prepare_price_changes."""
    np.random.seed(12)
    idx = pd.date_range("2024-01-01", periods=200, freq="h", tz="UTC")
    prices = pd.Series(0.50 + np.cumsum(np.random.normal(0, 0.005, 200)), index=idx)
    return prices.clip(0, 1)


@pytest.fixture
def detector():
    return BenfordDetector()


# ── Tests ──────────────────────────────────────────────────────────

class TestBenfordTheory:

    def test_benford_probs_sum_to_one(self):
        total = sum(BENFORD_PROBS.values())
        assert abs(total - 1.0) < 1e-10

    def test_benford_probs_digit_1_highest(self):
        assert BENFORD_PROBS[1] > BENFORD_PROBS[2]
        assert BENFORD_PROBS[2] > BENFORD_PROBS[9]


class TestFirstDigitExtraction:

    def test_basic_extraction(self):
        values = pd.Series([123, 456, 789, 12, 5])
        digits = BenfordDetector.extract_first_digits(values)
        expected = [1, 4, 7, 1, 5]
        assert list(digits) == expected

    def test_decimal_extraction(self):
        values = pd.Series([0.00345, 0.078, 0.91])
        digits = BenfordDetector.extract_first_digits(values)
        expected = [3, 7, 9]
        assert list(digits) == expected

    def test_negative_values(self):
        values = pd.Series([-123, -45, -6])
        digits = BenfordDetector.extract_first_digits(values)
        expected = [1, 4, 6]
        assert list(digits) == expected

    def test_zeros_dropped(self):
        values = pd.Series([0, 0, 123, 0])
        digits = BenfordDetector.extract_first_digits(values)
        assert len(digits) == 1
        assert digits.iloc[0] == 1

    def test_nan_dropped(self):
        values = pd.Series([np.nan, 123, np.nan, 456])
        digits = BenfordDetector.extract_first_digits(values)
        assert len(digits) == 2

    def test_empty_series(self):
        values = pd.Series(dtype=float)
        digits = BenfordDetector.extract_first_digits(values)
        assert len(digits) == 0


class TestComputeDistribution:

    def test_distribution_sums_to_one(self, detector, benford_conforming_data):
        digits = detector.extract_first_digits(benford_conforming_data)
        dist = detector.compute_distribution(digits)
        total = sum(dist.values())
        assert abs(total - 1.0) < 1e-10

    def test_all_digits_present(self, detector, benford_conforming_data):
        digits = detector.extract_first_digits(benford_conforming_data)
        dist = detector.compute_distribution(digits)
        for d in range(1, 10):
            assert d in dist


class TestChiSquaredTest:

    def test_conforming_data_passes(self, detector, benford_conforming_data):
        digits = detector.extract_first_digits(benford_conforming_data)
        result = detector.chi_squared_test(digits)
        assert result["is_conforming"] is True
        assert result["p_value"] > 0.05

    def test_non_conforming_data_fails(self, detector, non_conforming_data):
        digits = detector.extract_first_digits(non_conforming_data)
        result = detector.chi_squared_test(digits)
        assert result["is_conforming"] is False

    def test_small_sample_returns_none(self, detector):
        digits = pd.Series([1, 2, 3, 4, 5])
        result = detector.chi_squared_test(digits)
        assert result["is_conforming"] is None
        assert "error" in result


class TestMADTest:

    def test_conforming_data(self, detector, benford_conforming_data):
        digits = detector.extract_first_digits(benford_conforming_data)
        result = detector.mad_test(digits)
        assert result["is_conforming"] is True
        assert result["conformity_level"] in ("close", "acceptable")

    def test_non_conforming_data(self, detector, non_conforming_data):
        digits = detector.extract_first_digits(non_conforming_data)
        result = detector.mad_test(digits)
        assert result["conformity_level"] in ("marginal", "nonconforming")


class TestFullAnalysis:

    def test_analyze_returns_all_keys(self, detector, benford_conforming_data):
        result = detector.analyze(benford_conforming_data)
        assert "first_digits" in result
        assert "observed_distribution" in result
        assert "expected_distribution" in result
        assert "chi_squared" in result
        assert "ks_test" in result
        assert "mad_test" in result
        assert "overall_conforming" in result

    def test_conforming_data_overall(self, detector, benford_conforming_data):
        result = detector.analyze(benford_conforming_data)
        assert result["overall_conforming"] is True

    def test_non_conforming_data_overall(self, detector, non_conforming_data):
        result = detector.analyze(non_conforming_data)
        assert result["overall_conforming"] is False


class TestSlidingWindow:

    def test_window_analysis_returns_list(self, detector, benford_conforming_data):
        results = detector.sliding_window_analysis(benford_conforming_data)
        assert isinstance(results, list)
        assert len(results) > 0

    def test_window_result_keys(self, detector, benford_conforming_data):
        results = detector.sliding_window_analysis(benford_conforming_data)
        w = results[0]
        assert "window_start_idx" in w
        assert "window_end_idx" in w
        assert "chi_squared_stat" in w
        assert "mad" in w

    def test_anomaly_windows(self, detector, non_conforming_data):
        results = detector.sliding_window_analysis(non_conforming_data)
        anomalies = detector.get_anomaly_windows(results)
        assert isinstance(anomalies, list)


class TestPreparePriceChanges:

    def test_output_positive(self, price_series):
        changes = prepare_price_changes(price_series)
        assert (changes > 0).all()

    def test_output_length(self, price_series):
        changes = prepare_price_changes(price_series)
        # Should be shorter than input (diff drops first + zeros removed)
        assert len(changes) <= len(price_series) - 1


class TestRunBenfordAnalysis:

    def test_returns_all_keys(self, benford_conforming_data):
        result = run_benford_analysis(benford_conforming_data)
        assert "analysis" in result
        assert "summary" in result
        assert "window_results" in result
        assert "anomaly_windows" in result
