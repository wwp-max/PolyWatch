# core_analysis/zscore_detector.py
"""
Z-Score based anomaly detector for PolyWatch.

Uses multi-scale rolling z-scores and return spike detection to identify
abnormal price movements in prediction market data.

Member C — Core Algorithm Module (Phase 1)
"""
import pandas as pd
import numpy as np
from dataclasses import dataclass
from typing import Optional


@dataclass
class ZScoreConfig:
    """Configuration for Z-Score anomaly detector."""
    # Rolling window sizes (number of data points)
    short_window: int = 6
    medium_window: int = 24
    long_window: int = 72

    # Z-score threshold for anomaly flagging
    z_threshold: float = 2.5

    # Absolute return spike threshold (e.g. 0.05 = 5% move)
    return_spike_threshold: float = 0.05

    # Severity thresholds
    high_severity_z: float = 4.0
    medium_severity_z: float = 3.0

    # Cluster detection: anomalies within this many points are one cluster
    cluster_gap: int = 3


class ZScoreDetector:
    """
    Multi-scale Z-Score anomaly detector.

    Computes rolling z-scores at short/medium/long windows, flags points
    where any z-score exceeds the threshold, and detects return spikes.

    Usage:
        detector = ZScoreDetector()
        result_df = detector.detect(price_series)
    """

    def __init__(self, config: Optional[ZScoreConfig] = None,
                 window: int = None, threshold: float = None):
        """
        Args:
            config: ZScoreConfig object (preferred)
            window: Legacy parameter — sets medium_window
            threshold: Legacy parameter — sets z_threshold
        """
        if config is not None:
            self.config = config
        else:
            self.config = ZScoreConfig()
            if window is not None:
                self.config.medium_window = window
                self.config.short_window = max(4, window // 4)
                self.config.long_window = window * 3
            if threshold is not None:
                self.config.z_threshold = threshold

        # Keep legacy attributes for backward compatibility
        self.window = self.config.medium_window
        self.threshold = self.config.z_threshold

    def detect(self, price_series: pd.Series) -> pd.DataFrame:
        """
        Run multi-scale z-score detection on a price series.

        Returns:
            DataFrame with columns:
                price, z_short, z_medium, z_long, z_max,
                return_spike, is_anomaly, severity
        """
        cfg = self.config

        # Rolling z-scores at multiple scales
        def rolling_z(series, window):
            mu = series.rolling(window, min_periods=max(2, window // 2)).mean()
            sigma = series.rolling(window, min_periods=max(2, window // 2)).std()
            sigma = sigma.replace(0, np.nan)
            return (series - mu) / sigma

        z_short = rolling_z(price_series, cfg.short_window)
        z_medium = rolling_z(price_series, cfg.medium_window)
        z_long = rolling_z(price_series, cfg.long_window)

        # Maximum absolute z-score across all windows
        z_max = pd.concat([z_short.abs(), z_medium.abs(), z_long.abs()], axis=1).max(axis=1)

        # Return spike detection
        returns = price_series.diff().abs()
        return_spike = returns >= cfg.return_spike_threshold

        # Anomaly flag: z-score exceeds threshold OR return spike
        is_anomaly = (z_max >= cfg.z_threshold) | return_spike

        # Severity classification
        severity = pd.Series("none", index=price_series.index)
        severity[is_anomaly] = "low"
        severity[z_max >= cfg.medium_severity_z] = "medium"
        severity[z_max >= cfg.high_severity_z] = "high"
        severity[return_spike & (z_max < cfg.medium_severity_z)] = "medium"

        result = pd.DataFrame({
            "price": price_series,
            "z_short": z_short,
            "z_medium": z_medium,
            "z_long": z_long,
            "z_max": z_max,
            "z_score": z_medium,  # backward compat
            "return_spike": return_spike,
            "is_anomaly": is_anomaly,
            "severity": severity,
        })

        return result


# ── Convenience Functions ──────────────────────────────────────────────

def _count_clusters(is_anomaly: pd.Series, gap: int = 3) -> int:
    """Count anomaly clusters (groups separated by >= gap normal points)."""
    anomaly_indices = np.where(is_anomaly.values)[0]
    if len(anomaly_indices) == 0:
        return 0
    clusters = 1
    for i in range(1, len(anomaly_indices)):
        if anomaly_indices[i] - anomaly_indices[i - 1] > gap:
            clusters += 1
    return clusters


def run_zscore_analysis(price_series: pd.Series,
                        config: Optional[ZScoreConfig] = None) -> dict:
    """
    One-call convenience function for Z-Score analysis.

    Args:
        price_series: Price data (Series with DatetimeIndex)
        config: Optional ZScoreConfig

    Returns:
        {
            result_df: full DataFrame,
            summary: {anomaly_points, anomaly_rate, high_severity, clusters, ...},
            events: list of anomaly event dicts for db_interface.write_anomaly(),
        }
    """
    cfg = config or ZScoreConfig()
    detector = ZScoreDetector(config=cfg)
    result_df = detector.detect(price_series)

    n_anomaly = int(result_df["is_anomaly"].sum())
    n_total = len(result_df)
    anomaly_rate = round(100.0 * n_anomaly / n_total, 2) if n_total > 0 else 0.0
    n_high = int((result_df["severity"] == "high").sum())
    n_medium = int((result_df["severity"] == "medium").sum())
    clusters = _count_clusters(result_df["is_anomaly"], cfg.cluster_gap)

    summary = {
        "anomaly_points": n_anomaly,
        "anomaly_rate": anomaly_rate,
        "high_severity": n_high,
        "medium_severity": n_medium,
        "clusters": clusters,
        "data_points": n_total,
        "config": {
            "short_window": cfg.short_window,
            "medium_window": cfg.medium_window,
            "long_window": cfg.long_window,
            "z_threshold": cfg.z_threshold,
            "return_spike_threshold": cfg.return_spike_threshold,
        },
    }

    # Build anomaly event list for database writes
    events = []
    anomaly_rows = result_df[result_df["is_anomaly"]]
    for idx, row in anomaly_rows.iterrows():
        events.append({
            "detected_at": idx,
            "event_type": "zscore_spike",
            "severity": row["severity"] if row["severity"] != "none" else "low",
            "detail": {
                "z_max": round(float(row["z_max"]), 4) if pd.notna(row["z_max"]) else None,
                "z_short": round(float(row["z_short"]), 4) if pd.notna(row["z_short"]) else None,
                "z_medium": round(float(row["z_medium"]), 4) if pd.notna(row["z_medium"]) else None,
                "price": round(float(row["price"]), 6) if pd.notna(row["price"]) else None,
                "return_spike": bool(row["return_spike"]),
            },
        })

    return {
        "result_df": result_df,
        "summary": summary,
        "events": events,
    }


if __name__ == "__main__":
    # Demo with synthetic data
    np.random.seed(42)
    prices = pd.Series(np.random.normal(100, 1, 200))

    # Inject anomaly spike
    prices.iloc[120] += 10

    detector = ZScoreDetector(window=20, threshold=2.5)
    result = detector.detect(prices)

    print("Anomalies detected:", result["is_anomaly"].sum())
    print(result[result["is_anomaly"] == True])

    # Test run_zscore_analysis
    print("\n--- run_zscore_analysis ---")
    analysis = run_zscore_analysis(prices)
    print(f"Summary: {analysis['summary']}")
    print(f"Events count: {len(analysis['events'])}")

