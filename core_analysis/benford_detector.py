# core_analysis/benford_detector.py
"""
Benford's Law anomaly detector for PolyWatch.

Detects artificially fabricated trading data by checking whether the
first-digit distribution of numerical values (trade sizes, price changes,
volumes) conforms to Benford's Law.

Theory:
  In naturally occurring datasets, the leading digit d (1-9) appears with
  probability P(d) = log10(1 + 1/d). Deviation from this distribution
  suggests data manipulation.

Supports:
  - Full-period Benford analysis
  - Sliding-window Benford analysis (detect temporal anomalies)
  - Chi-squared goodness-of-fit test
  - Kolmogorov-Smirnov test
  - Mean Absolute Deviation (MAD) conformity metric

Member C — Core Algorithm Module (Phase 2)
"""
import math
import pandas as pd
import numpy as np
from dataclasses import dataclass
from typing import Optional

try:
    from scipy import stats as scipy_stats
    HAS_SCIPY = True
except ImportError:
    HAS_SCIPY = False


# ── Benford theoretical distribution ───────────────────────────────

BENFORD_PROBS = {d: math.log10(1 + 1 / d) for d in range(1, 10)}
# {1: 0.3010, 2: 0.1761, 3: 0.1249, 4: 0.0969, 5: 0.0792,
#  6: 0.0669, 7: 0.0580, 8: 0.0512, 9: 0.0458}


@dataclass
class BenfordConfig:
    """Configuration for Benford's Law detector."""
    # Statistical significance level
    alpha: float = 0.05

    # MAD conformity thresholds (per Nigrini 2012)
    mad_close_conformity: float = 0.006
    mad_acceptable_conformity: float = 0.012
    mad_marginal_conformity: float = 0.015
    # > marginal = nonconformity

    # Sliding window size (number of data points)
    window_size: int = 100

    # Sliding window step
    window_step: int = 50

    # Minimum data points required for meaningful analysis
    min_sample_size: int = 50


class BenfordDetector:
    """
    Benford's Law conformity detector.

    Can analyze:
      - Trade sizes / volumes (ideal use case)
      - Price changes / returns (MVP when trade data unavailable)
      - Any numerical dataset

    Usage:
        detector = BenfordDetector()

        # Analyze a full series
        result = detector.analyze(data_series)

        # Sliding window analysis
        windows = detector.sliding_window_analysis(data_series)
    """

    def __init__(self, config: Optional[BenfordConfig] = None):
        self.config = config or BenfordConfig()

    # ── First Digit Extraction ─────────────────────────────────────

    @staticmethod
    def extract_first_digits(values: pd.Series) -> pd.Series:
        """
        Extract the first significant digit (1-9) from a Series of numbers.
        Zeros and NaN are dropped.
        """
        abs_values = values.abs().dropna()
        abs_values = abs_values[abs_values > 0]
        if abs_values.empty:
            return pd.Series(dtype=int)

        # Extract first digit: divide by 10^floor(log10(x))
        log_vals = np.log10(abs_values.values.astype(float))
        first_digits = np.floor(abs_values.values.astype(float) / (10 ** np.floor(log_vals)))
        first_digits = first_digits.astype(int)
        # Clamp to 1-9 (handle edge cases)
        first_digits = np.clip(first_digits, 1, 9)

        return pd.Series(first_digits, index=abs_values.index, name="first_digit")

    # ── Distribution Computation ───────────────────────────────────

    @staticmethod
    def compute_distribution(first_digits: pd.Series) -> dict:
        """
        Compute the observed frequency distribution of first digits.

        Returns:
            Dict {1: freq, 2: freq, ..., 9: freq} where freq sums to 1.0
        """
        counts = first_digits.value_counts()
        total = counts.sum()
        if total == 0:
            return {d: 0.0 for d in range(1, 10)}

        dist = {}
        for d in range(1, 10):
            dist[d] = counts.get(d, 0) / total
        return dist

    # ── Statistical Tests ──────────────────────────────────────────

    def chi_squared_test(self, first_digits: pd.Series) -> dict:
        """
        Chi-squared goodness-of-fit test against Benford distribution.

        Returns:
            {statistic, p_value, is_conforming, n}
        """
        n = len(first_digits)
        if n < self.config.min_sample_size:
            return {
                "statistic": None, "p_value": None,
                "is_conforming": None, "n": n,
                "error": f"Sample too small ({n} < {self.config.min_sample_size})"
            }

        observed = first_digits.value_counts().reindex(range(1, 10), fill_value=0)
        expected = pd.Series({d: BENFORD_PROBS[d] * n for d in range(1, 10)})

        if HAS_SCIPY:
            stat, p_value = scipy_stats.chisquare(observed.values, expected.values)
        else:
            # Manual chi-squared calculation
            stat = float(((observed.values - expected.values) ** 2 / expected.values).sum())
            # Degrees of freedom = 8 (9 categories - 1)
            # Approximate p-value using survival function
            p_value = 1.0  # Conservative fallback without scipy

        return {
            "statistic": round(float(stat), 4),
            "p_value": round(float(p_value), 6),
            "is_conforming": float(p_value) >= self.config.alpha,
            "n": n,
        }

    def ks_test(self, first_digits: pd.Series) -> dict:
        """
        Kolmogorov-Smirnov test against Benford CDF.

        Returns:
            {statistic, p_value, is_conforming, n}
        """
        n = len(first_digits)
        if n < self.config.min_sample_size or not HAS_SCIPY:
            return {
                "statistic": None, "p_value": None,
                "is_conforming": None, "n": n,
            }

        # Build Benford CDF
        benford_cdf = np.cumsum([BENFORD_PROBS[d] for d in range(1, 10)])

        # Build observed CDF
        counts = first_digits.value_counts().reindex(range(1, 10), fill_value=0)
        observed_cdf = np.cumsum(counts.values / n)

        # KS statistic = max |observed_cdf - expected_cdf|
        ks_stat = float(np.max(np.abs(observed_cdf - benford_cdf)))

        # Approximate p-value using KS distribution
        # For discrete data this is conservative
        p_value = float(np.exp(-2 * n * ks_stat ** 2))  # Simplified

        return {
            "statistic": round(ks_stat, 4),
            "p_value": round(p_value, 6),
            "is_conforming": p_value >= self.config.alpha,
            "n": n,
        }

    def mad_test(self, first_digits: pd.Series) -> dict:
        """
        Mean Absolute Deviation (MAD) conformity test.
        Uses Nigrini (2012) thresholds for first-digit test.

        Returns:
            {mad, conformity_level, is_conforming, n}
        """
        n = len(first_digits)
        if n < self.config.min_sample_size:
            return {
                "mad": None, "conformity_level": None,
                "is_conforming": None, "n": n,
            }

        observed = self.compute_distribution(first_digits)
        mad = sum(abs(observed[d] - BENFORD_PROBS[d]) for d in range(1, 10)) / 9

        if mad <= self.config.mad_close_conformity:
            level = "close"
        elif mad <= self.config.mad_acceptable_conformity:
            level = "acceptable"
        elif mad <= self.config.mad_marginal_conformity:
            level = "marginal"
        else:
            level = "nonconforming"

        return {
            "mad": round(mad, 6),
            "conformity_level": level,
            "is_conforming": level in ("close", "acceptable"),
            "n": n,
        }

    # ── Full Analysis ──────────────────────────────────────────────

    def analyze(self, values: pd.Series) -> dict:
        """
        Run full Benford analysis on a Series of numerical values.

        Args:
            values: Any numerical Series (trade sizes, price changes, etc.)

        Returns:
            {
                first_digits, observed_distribution, expected_distribution,
                chi_squared, ks_test, mad_test,
                overall_conforming, n_valid, n_total
            }
        """
        first_digits = self.extract_first_digits(values)
        observed = self.compute_distribution(first_digits)

        chi2 = self.chi_squared_test(first_digits)
        ks = self.ks_test(first_digits)
        mad = self.mad_test(first_digits)

        # Overall conformity: majority vote of available tests
        votes = []
        if chi2.get("is_conforming") is not None:
            votes.append(chi2["is_conforming"])
        if ks.get("is_conforming") is not None:
            votes.append(ks["is_conforming"])
        if mad.get("is_conforming") is not None:
            votes.append(mad["is_conforming"])

        overall = sum(votes) > len(votes) / 2 if votes else None

        return {
            "first_digits": first_digits,
            "observed_distribution": observed,
            "expected_distribution": dict(BENFORD_PROBS),
            "chi_squared": chi2,
            "ks_test": ks,
            "mad_test": mad,
            "overall_conforming": overall,
            "n_valid": len(first_digits),
            "n_total": len(values),
        }

    # ── Sliding Window Analysis ────────────────────────────────────

    def sliding_window_analysis(self, values: pd.Series,
                                timestamps: Optional[pd.DatetimeIndex] = None
                                ) -> list[dict]:
        """
        Run Benford analysis over sliding windows to detect temporal anomalies.

        Args:
            values: Numerical series to analyze
            timestamps: Optional DatetimeIndex for time labeling

        Returns:
            List of window results with added time_start, time_end fields
        """
        n = len(values)
        results = []

        for start in range(0, n - self.config.window_size + 1, self.config.window_step):
            end = start + self.config.window_size
            window_values = values.iloc[start:end]

            first_digits = self.extract_first_digits(window_values)
            chi2 = self.chi_squared_test(first_digits)
            mad = self.mad_test(first_digits)

            window_result = {
                "window_start_idx": start,
                "window_end_idx": end,
                "chi_squared_stat": chi2.get("statistic"),
                "chi_squared_p": chi2.get("p_value"),
                "mad": mad.get("mad"),
                "conformity_level": mad.get("conformity_level"),
                "is_conforming": chi2.get("is_conforming"),
                "n": chi2.get("n", 0),
            }

            if timestamps is not None and len(timestamps) > end - 1:
                window_result["time_start"] = timestamps[start]
                window_result["time_end"] = timestamps[end - 1]

            results.append(window_result)

        return results

    def get_anomaly_windows(self, window_results: list[dict]) -> list[dict]:
        """
        Filter sliding window results for non-conforming windows.

        Returns:
            List of windows where Benford's Law is violated.
        """
        return [w for w in window_results if w.get("is_conforming") is False]

    def get_anomaly_events(self, window_results: list[dict],
                           market_slug: str = "") -> list[dict]:
        """
        Convert non-conforming windows to anomaly event dicts for db_interface.write_anomaly().
        """
        events = []
        for w in self.get_anomaly_windows(window_results):
            detail = {
                "chi_squared_stat": w.get("chi_squared_stat"),
                "chi_squared_p": w.get("chi_squared_p"),
                "mad": w.get("mad"),
                "conformity_level": w.get("conformity_level"),
                "window_size": self.config.window_size,
                "market_slug": market_slug,
            }
            detected_at = w.get("time_end", w.get("time_start"))
            events.append({
                "detected_at": detected_at,
                "event_type": "benford_violation",
                "severity": "high" if w.get("conformity_level") == "nonconforming" else "medium",
                "detail": detail,
            })
        return events

    # ── Summary ────────────────────────────────────────────────────

    def summary(self, analysis_result: dict) -> dict:
        """Generate a human-readable summary of full analysis."""
        return {
            "n_valid": analysis_result["n_valid"],
            "n_total": analysis_result["n_total"],
            "overall_conforming": analysis_result["overall_conforming"],
            "chi_squared_p": analysis_result["chi_squared"].get("p_value"),
            "mad": analysis_result["mad_test"].get("mad"),
            "conformity_level": analysis_result["mad_test"].get("conformity_level"),
        }


# ── Convenience function ────────────────────────────────────────────

def prepare_price_changes(price_series: pd.Series) -> pd.Series:
    """
    Prepare price data for Benford analysis when trade data is unavailable.
    Uses absolute price changes (deltas) as proxy for trading activity.

    Multiplies by 10000 to get integer-like values suitable for first-digit extraction.
    """
    deltas = price_series.diff().dropna().abs()
    # Scale up to get meaningful first digits (avoid tiny decimals)
    scaled = deltas * 10000
    # Remove zeros
    return scaled[scaled > 0]


def run_benford_analysis(values: pd.Series,
                         config: Optional[BenfordConfig] = None) -> dict:
    """
    One-call convenience function for Benford analysis.

    Returns:
        {analysis, summary, window_results, anomaly_windows}
    """
    detector = BenfordDetector(config)
    analysis = detector.analyze(values)

    # Also run sliding window if enough data
    window_results = []
    if len(values) >= (config or BenfordConfig()).window_size:
        timestamps = values.index if isinstance(values.index, pd.DatetimeIndex) else None
        window_results = detector.sliding_window_analysis(values, timestamps)

    return {
        "analysis": analysis,
        "summary": detector.summary(analysis),
        "window_results": window_results,
        "anomaly_windows": detector.get_anomaly_windows(window_results),
    }


if __name__ == "__main__":
    # Demo with synthetic data
    np.random.seed(42)

    # Generate Benford-conforming data (exponential)
    benford_data = pd.Series(np.random.exponential(scale=100, size=500))
    print("=== Benford-conforming data (exponential) ===")
    result = run_benford_analysis(benford_data)
    print(f"Conforming: {result['summary']['overall_conforming']}")
    print(f"Chi-squared p-value: {result['summary']['chi_squared_p']}")
    print(f"MAD: {result['summary']['mad']}, Level: {result['summary']['conformity_level']}")

    # Generate non-conforming data (uniform)
    uniform_data = pd.Series(np.random.uniform(100, 999, size=500))
    print("\n=== Non-conforming data (uniform) ===")
    result2 = run_benford_analysis(uniform_data)
    print(f"Conforming: {result2['summary']['overall_conforming']}")
    print(f"Chi-squared p-value: {result2['summary']['chi_squared_p']}")
    print(f"MAD: {result2['summary']['mad']}, Level: {result2['summary']['conformity_level']}")
