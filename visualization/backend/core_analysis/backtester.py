# core_analysis/backtester.py
"""
Backtesting framework for PolyWatch anomaly detection algorithms.

Validates algorithm performance against the 2024 US Presidential Election
historical data with known event labels. Supports:
  - Event-based ground truth labeling (known market-moving events)
  - Running all 3 detectors (Z-Score, Benford, Whale Alert) on historical data
  - Grid search for parameter optimization
  - Precision / Recall / F1 metrics
  - False Positive / False Negative analysis
  - ROC-style threshold sweep

Member C — Core Algorithm Module (Phase 4)
"""
import pandas as pd
import numpy as np
from dataclasses import dataclass, field
from typing import Optional, Callable
from datetime import timedelta

from core_analysis.zscore_detector import ZScoreDetector, ZScoreConfig, run_zscore_analysis
from core_analysis.benford_detector import (
    BenfordDetector, BenfordConfig, prepare_price_changes, run_benford_analysis,
)
from core_analysis.whale_alert import (
    WhaleAlert, WhaleConfig, simulate_trades_from_prices, run_whale_analysis,
)


# ══════════════════════════════════════════════════════════════════════
#  2024 US Presidential Election — Known Event Timeline
# ══════════════════════════════════════════════════════════════════════

ELECTION_EVENTS = [
    {
        "date": "2024-01-15",
        "name": "Iowa Caucus",
        "description": "Trump wins Iowa caucus decisively",
        "expected_direction": "up",
        "expected_magnitude": "medium",
    },
    {
        "date": "2024-03-05",
        "name": "Super Tuesday",
        "description": "Trump sweeps Super Tuesday primaries",
        "expected_direction": "up",
        "expected_magnitude": "medium",
    },
    {
        "date": "2024-06-27",
        "name": "Biden-Trump Debate",
        "description": "First debate, Biden performs poorly",
        "expected_direction": "up",
        "expected_magnitude": "large",
    },
    {
        "date": "2024-07-13",
        "name": "Trump Assassination Attempt",
        "description": "Trump shot at rally in Butler, PA",
        "expected_direction": "up",
        "expected_magnitude": "large",
    },
    {
        "date": "2024-07-21",
        "name": "Biden Drops Out",
        "description": "Biden withdraws, endorses Harris",
        "expected_direction": "down",
        "expected_magnitude": "large",
    },
    {
        "date": "2024-08-22",
        "name": "DNC Convention",
        "description": "Democratic National Convention, Harris momentum",
        "expected_direction": "down",
        "expected_magnitude": "medium",
    },
    {
        "date": "2024-09-10",
        "name": "Harris-Trump Debate",
        "description": "Harris-Trump presidential debate",
        "expected_direction": "down",
        "expected_magnitude": "medium",
    },
    {
        "date": "2024-11-05",
        "name": "Election Day",
        "description": "Election day, price converges to outcome",
        "expected_direction": "up",
        "expected_magnitude": "large",
    },
]


# ══════════════════════════════════════════════════════════════════════
#  Ground Truth Label Generator
# ══════════════════════════════════════════════════════════════════════

@dataclass
class LabelConfig:
    """Configuration for ground truth label generation."""
    # How many hours around an event to mark as "expected anomaly"
    event_window_hours_before: int = 6
    event_window_hours_after: int = 24

    # Price change threshold to also mark as "true anomaly" (beyond events)
    price_change_threshold: float = 0.03  # 3% absolute change in one step


def generate_ground_truth(price_series: pd.Series,
                          events: list[dict] = None,
                          config: LabelConfig = None) -> pd.Series:
    """
    Generate ground truth labels for a price series.

    Labels:
        0 = normal (no known event, no large price move)
        1 = expected anomaly (near a known event OR large price move)

    Args:
        price_series: Series with DatetimeIndex
        events: List of event dicts with 'date' field (defaults to ELECTION_EVENTS)
        config: Label configuration

    Returns:
        Series of 0/1 labels aligned with price_series index
    """
    if events is None:
        events = ELECTION_EVENTS
    if config is None:
        config = LabelConfig()

    labels = pd.Series(0, index=price_series.index, dtype=int)

    # Mark event windows
    for event in events:
        event_time = pd.Timestamp(event["date"], tz="UTC")
        window_start = event_time - timedelta(hours=config.event_window_hours_before)
        window_end = event_time + timedelta(hours=config.event_window_hours_after)
        mask = (labels.index >= window_start) & (labels.index <= window_end)
        labels[mask] = 1

    # Also mark large price changes as expected anomalies
    returns = price_series.diff().abs()
    large_moves = returns >= config.price_change_threshold
    labels[large_moves] = 1

    return labels


# ══════════════════════════════════════════════════════════════════════
#  Metrics Computation
# ══════════════════════════════════════════════════════════════════════

def compute_metrics(y_true: pd.Series, y_pred: pd.Series) -> dict:
    """
    Compute classification metrics for anomaly detection.

    Args:
        y_true: Ground truth labels (0 or 1)
        y_pred: Predicted labels (0 or 1)

    Returns:
        Dict with TP, FP, TN, FN, precision, recall, F1, accuracy, FPR, FNR
    """
    # Align indices
    common = y_true.index.intersection(y_pred.index)
    yt = y_true.loc[common].values.astype(int)
    yp = y_pred.loc[common].values.astype(int)

    tp = int(((yt == 1) & (yp == 1)).sum())
    fp = int(((yt == 0) & (yp == 1)).sum())
    tn = int(((yt == 0) & (yp == 0)).sum())
    fn = int(((yt == 1) & (yp == 0)).sum())

    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0
    accuracy = (tp + tn) / len(yt) if len(yt) > 0 else 0.0
    fpr = fp / (fp + tn) if (fp + tn) > 0 else 0.0
    fnr = fn / (fn + tp) if (fn + tp) > 0 else 0.0

    return {
        "TP": tp,
        "FP": fp,
        "TN": tn,
        "FN": fn,
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1": round(f1, 4),
        "accuracy": round(accuracy, 4),
        "FPR": round(fpr, 4),
        "FNR": round(fnr, 4),
        "total": len(yt),
        "positives": int(yt.sum()),
        "negatives": int((yt == 0).sum()),
    }


# ══════════════════════════════════════════════════════════════════════
#  Backtester Class
# ══════════════════════════════════════════════════════════════════════

class Backtester:
    """
    Backtesting engine that runs detectors against labeled historical data.

    Usage:
        bt = Backtester(price_series)
        zscore_result = bt.run_zscore()
        metrics = bt.evaluate_zscore(zscore_result)
        grid = bt.grid_search_zscore()
    """

    def __init__(self, price_series: pd.Series,
                 events: list[dict] = None,
                 label_config: LabelConfig = None):
        """
        Args:
            price_series: Historical price data with DatetimeIndex
            events: Known event list (defaults to ELECTION_EVENTS)
            label_config: Label generation config
        """
        self.price_series = price_series
        self.events = events or ELECTION_EVENTS
        self.label_config = label_config or LabelConfig()
        self.ground_truth = generate_ground_truth(
            price_series, self.events, self.label_config
        )

    # ── Z-Score Backtesting ────────────────────────────────────────

    def run_zscore(self, config: ZScoreConfig = None) -> dict:
        """Run Z-Score detector and return full results."""
        return run_zscore_analysis(self.price_series, config)

    def evaluate_zscore(self, zscore_result: dict = None,
                        config: ZScoreConfig = None) -> dict:
        """
        Evaluate Z-Score detector against ground truth.

        Returns:
            {metrics, config_used, anomaly_count, ...}
        """
        if zscore_result is None:
            zscore_result = self.run_zscore(config)

        result_df = zscore_result["result_df"]
        y_pred = result_df["is_anomaly"].astype(int)

        metrics = compute_metrics(self.ground_truth, y_pred)
        cfg = config or ZScoreConfig()
        metrics["config"] = {
            "short_window": cfg.short_window,
            "medium_window": cfg.medium_window,
            "long_window": cfg.long_window,
            "z_threshold": cfg.z_threshold,
            "return_spike_threshold": cfg.return_spike_threshold,
        }
        metrics["detector"] = "zscore"
        return metrics

    def grid_search_zscore(self,
                           z_thresholds: list[float] = None,
                           short_windows: list[int] = None,
                           medium_windows: list[int] = None,
                           return_spike_thresholds: list[float] = None,
                           ) -> pd.DataFrame:
        """
        Grid search over Z-Score parameters to find optimal config.

        Returns:
            DataFrame of all parameter combinations and their metrics,
            sorted by F1 score descending.
        """
        if z_thresholds is None:
            z_thresholds = [2.0, 2.5, 3.0, 3.5]
        if short_windows is None:
            short_windows = [4, 6, 12]
        if medium_windows is None:
            medium_windows = [18, 24, 48]
        if return_spike_thresholds is None:
            return_spike_thresholds = [0.03, 0.05, 0.08]

        results = []
        total = (len(z_thresholds) * len(short_windows) *
                 len(medium_windows) * len(return_spike_thresholds))
        count = 0

        for zt in z_thresholds:
            for sw in short_windows:
                for mw in medium_windows:
                    for rst in return_spike_thresholds:
                        count += 1
                        config = ZScoreConfig(
                            short_window=sw,
                            medium_window=mw,
                            z_threshold=zt,
                            return_spike_threshold=rst,
                        )
                        try:
                            metrics = self.evaluate_zscore(config=config)
                            row = {
                                "z_threshold": zt,
                                "short_window": sw,
                                "medium_window": mw,
                                "return_spike_threshold": rst,
                                "precision": metrics["precision"],
                                "recall": metrics["recall"],
                                "f1": metrics["f1"],
                                "accuracy": metrics["accuracy"],
                                "FPR": metrics["FPR"],
                                "FNR": metrics["FNR"],
                                "TP": metrics["TP"],
                                "FP": metrics["FP"],
                                "FN": metrics["FN"],
                                "TN": metrics["TN"],
                            }
                            results.append(row)
                        except Exception as e:
                            results.append({
                                "z_threshold": zt,
                                "short_window": sw,
                                "medium_window": mw,
                                "return_spike_threshold": rst,
                                "error": str(e),
                            })

        df = pd.DataFrame(results)
        if "f1" in df.columns:
            df = df.sort_values("f1", ascending=False).reset_index(drop=True)
        return df

    # ── Benford Backtesting ────────────────────────────────────────

    def run_benford(self, config: BenfordConfig = None) -> dict:
        """Run Benford detector on price changes."""
        price_changes = prepare_price_changes(self.price_series)
        return run_benford_analysis(price_changes, config)

    def evaluate_benford(self, benford_result: dict = None,
                         config: BenfordConfig = None) -> dict:
        """
        Evaluate Benford detector against ground truth.

        Benford works on windows, so we map non-conforming windows
        back to individual timestamps for comparison.
        """
        if benford_result is None:
            benford_result = self.run_benford(config)

        # Create prediction series (default all 0)
        y_pred = pd.Series(0, index=self.price_series.index, dtype=int)

        # Mark non-conforming windows as anomalies
        for w in benford_result.get("anomaly_windows", []):
            ts = w.get("time_start")
            te = w.get("time_end")
            if ts is not None and te is not None:
                mask = (y_pred.index >= ts) & (y_pred.index <= te)
                y_pred[mask] = 1

        metrics = compute_metrics(self.ground_truth, y_pred)
        cfg = config or BenfordConfig()
        metrics["config"] = {
            "alpha": cfg.alpha,
            "window_size": cfg.window_size,
            "window_step": cfg.window_step,
            "min_sample_size": cfg.min_sample_size,
        }
        metrics["detector"] = "benford"
        metrics["n_anomaly_windows"] = len(benford_result.get("anomaly_windows", []))
        metrics["n_total_windows"] = len(benford_result.get("window_results", []))
        return metrics

    # ── Whale Alert Backtesting ────────────────────────────────────

    def run_whale(self, config: WhaleConfig = None,
                  trades: pd.DataFrame = None) -> dict:
        """
        Run Whale Alert detector. Uses simulated trades if none provided.
        """
        if trades is None:
            trades = simulate_trades_from_prices(self.price_series)
        return run_whale_analysis(trades, self.price_series, config)

    def evaluate_whale(self, whale_result: dict = None,
                       config: WhaleConfig = None,
                       trades: pd.DataFrame = None) -> dict:
        """
        Evaluate Whale Alert against ground truth.

        Maps whale trade timestamps back to price series timestamps.
        """
        if whale_result is None:
            whale_result = self.run_whale(config, trades)

        y_pred = pd.Series(0, index=self.price_series.index, dtype=int)

        # Mark whale trade timestamps as anomalies
        whale_trades = whale_result.get("whale_trades", pd.DataFrame())
        if not whale_trades.empty:
            timestamps = whale_trades.get("timestamp", whale_trades.index)
            for t in timestamps:
                if isinstance(t, pd.Timestamp):
                    # Mark nearest points in price series
                    diffs = abs(y_pred.index - t)
                    nearest_idx = diffs.argmin()
                    # Mark a small window around the whale trade
                    start = max(0, nearest_idx - 2)
                    end = min(len(y_pred), nearest_idx + 3)
                    y_pred.iloc[start:end] = 1

        # Also mark directional bias events
        for bias in whale_result.get("directional_events", []):
            ts = bias.get("time_start")
            te = bias.get("time_end")
            if ts is not None and te is not None:
                mask = (y_pred.index >= ts) & (y_pred.index <= te)
                y_pred[mask] = 1

        metrics = compute_metrics(self.ground_truth, y_pred)
        cfg = config or WhaleConfig()
        metrics["config"] = {
            "size_threshold": cfg.size_threshold,
            "cumulative_threshold": cfg.cumulative_threshold,
            "directional_bias_pct": cfg.directional_bias_pct,
        }
        metrics["detector"] = "whale_alert"
        metrics["n_whale_trades"] = len(whale_trades)
        metrics["n_directional_events"] = len(whale_result.get("directional_events", []))
        return metrics

    # ── Combined Evaluation ────────────────────────────────────────

    def evaluate_all(self) -> dict:
        """
        Run and evaluate all 3 detectors with default parameters.

        Returns:
            {
                zscore: metrics_dict,
                benford: metrics_dict,
                whale_alert: metrics_dict,
                ground_truth_summary: {total, positives, negatives},
                combined: metrics for union of all detectors,
            }
        """
        zscore_metrics = self.evaluate_zscore()
        benford_metrics = self.evaluate_benford()
        whale_metrics = self.evaluate_whale()

        # Combined: union of all detectors
        zscore_result = self.run_zscore()
        benford_result = self.run_benford()
        whale_result = self.run_whale()

        y_combined = pd.Series(0, index=self.price_series.index, dtype=int)

        # Z-Score predictions
        z_pred = zscore_result["result_df"]["is_anomaly"].astype(int)
        y_combined = y_combined.combine(z_pred, max, fill_value=0).astype(int)

        # Benford predictions
        for w in benford_result.get("anomaly_windows", []):
            ts, te = w.get("time_start"), w.get("time_end")
            if ts and te:
                mask = (y_combined.index >= ts) & (y_combined.index <= te)
                y_combined[mask] = 1

        # Whale predictions
        whale_trades = whale_result.get("whale_trades", pd.DataFrame())
        if not whale_trades.empty:
            for t in whale_trades.get("timestamp", whale_trades.index):
                if isinstance(t, pd.Timestamp):
                    diffs = abs(y_combined.index - t)
                    nearest_idx = diffs.argmin()
                    start = max(0, nearest_idx - 2)
                    end = min(len(y_combined), nearest_idx + 3)
                    y_combined.iloc[start:end] = 1

        combined_metrics = compute_metrics(self.ground_truth, y_combined)
        combined_metrics["detector"] = "combined"

        gt_summary = {
            "total": len(self.ground_truth),
            "positives": int(self.ground_truth.sum()),
            "negatives": int((self.ground_truth == 0).sum()),
            "positive_rate": round(self.ground_truth.mean() * 100, 2),
        }

        return {
            "zscore": zscore_metrics,
            "benford": benford_metrics,
            "whale_alert": whale_metrics,
            "combined": combined_metrics,
            "ground_truth_summary": gt_summary,
        }

    # ── Threshold Sweep (ROC-style) ────────────────────────────────

    def threshold_sweep_zscore(self,
                               thresholds: list[float] = None) -> pd.DataFrame:
        """
        Sweep Z-Score threshold to generate ROC-like curve data.

        Returns:
            DataFrame with columns: threshold, FPR, TPR (recall), precision, F1
        """
        if thresholds is None:
            thresholds = [1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0, 5.0, 6.0]

        # Run detection once with lowest threshold to get all z-scores
        low_config = ZScoreConfig(z_threshold=min(thresholds))
        result = self.run_zscore(low_config)
        result_df = result["result_df"]

        rows = []
        for t in sorted(thresholds):
            y_pred = (result_df["z_max"].abs() >= t).astype(int)
            m = compute_metrics(self.ground_truth, y_pred)
            rows.append({
                "threshold": t,
                "FPR": m["FPR"],
                "TPR": m["recall"],
                "precision": m["precision"],
                "f1": m["f1"],
                "TP": m["TP"],
                "FP": m["FP"],
            })

        return pd.DataFrame(rows)

    # ── Event-Level Analysis ───────────────────────────────────────

    def event_detection_report(self, zscore_result: dict = None) -> pd.DataFrame:
        """
        For each known event, check if the detector flagged any anomaly
        within the event window.

        Returns:
            DataFrame with one row per event: name, date, detected (bool),
            nearest_anomaly_distance_hours, peak_z_score
        """
        if zscore_result is None:
            zscore_result = self.run_zscore()

        result_df = zscore_result["result_df"]
        anomalies = result_df[result_df["is_anomaly"]]

        rows = []
        for event in self.events:
            event_time = pd.Timestamp(event["date"], tz="UTC")
            window_start = event_time - timedelta(
                hours=self.label_config.event_window_hours_before
            )
            window_end = event_time + timedelta(
                hours=self.label_config.event_window_hours_after
            )

            # Check if any anomaly falls within the window
            window_mask = (
                (anomalies.index >= window_start) &
                (anomalies.index <= window_end)
            )
            window_anomalies = anomalies[window_mask]

            detected = len(window_anomalies) > 0
            peak_z = float(window_anomalies["z_max"].max()) if detected else 0.0

            # Nearest anomaly distance
            if not anomalies.empty:
                distances = abs(anomalies.index - event_time)
                nearest_hours = distances.min().total_seconds() / 3600
            else:
                nearest_hours = float("inf")

            rows.append({
                "event_name": event["name"],
                "event_date": event["date"],
                "expected_magnitude": event["expected_magnitude"],
                "detected": detected,
                "anomalies_in_window": len(window_anomalies),
                "peak_z_score": round(peak_z, 2),
                "nearest_anomaly_hours": round(nearest_hours, 1),
            })

        return pd.DataFrame(rows)

    # ── Summary Report ─────────────────────────────────────────────

    def generate_report(self) -> dict:
        """
        Generate a comprehensive backtest report.

        Returns:
            {
                all_metrics: evaluate_all() result,
                event_report: event_detection_report DataFrame,
                grid_search_top5: top 5 Z-Score configs by F1,
                threshold_sweep: ROC-like data,
            }
        """
        all_metrics = self.evaluate_all()
        event_report = self.event_detection_report()
        grid_df = self.grid_search_zscore()
        threshold_df = self.threshold_sweep_zscore()

        return {
            "all_metrics": all_metrics,
            "event_report": event_report,
            "grid_search_top5": grid_df.head(5) if not grid_df.empty else grid_df,
            "threshold_sweep": threshold_df,
        }


# ══════════════════════════════════════════════════════════════════════
#  Convenience Function
# ══════════════════════════════════════════════════════════════════════

def run_backtest(price_series: pd.Series,
                 events: list[dict] = None) -> dict:
    """
    One-call convenience function to run full backtest.

    Args:
        price_series: Historical price data with DatetimeIndex
        events: Optional event list (defaults to 2024 election events)

    Returns:
        Full backtest report dict
    """
    bt = Backtester(price_series, events)
    return bt.generate_report()


if __name__ == "__main__":
    # Demo with synthetic 2024 election-like data
    np.random.seed(42)

    # Simulate ~300 days of hourly price data
    n_points = 300 * 24
    idx = pd.date_range("2024-01-05", periods=n_points, freq="h", tz="UTC")
    base = 0.50 + np.cumsum(np.random.normal(0, 0.001, n_points))

    # Inject known events
    event_effects = {
        "2024-01-15": 0.05,   # Iowa
        "2024-03-05": 0.04,   # Super Tuesday
        "2024-06-27": 0.10,   # Debate
        "2024-07-13": 0.08,   # Shooting
        "2024-07-21": -0.12,  # Biden drops out
        "2024-08-22": -0.06,  # DNC
        "2024-09-10": -0.04,  # Harris debate
        "2024-11-05": 0.20,   # Election day
    }
    prices = pd.Series(base, index=idx).clip(0.01, 0.99)
    for date_str, effect in event_effects.items():
        event_time = pd.Timestamp(date_str, tz="UTC")
        mask = (prices.index >= event_time) & (
            prices.index < event_time + timedelta(hours=12)
        )
        prices[mask] += effect

    prices = prices.clip(0.01, 0.99)

    print("Running backtest on synthetic data...")
    bt = Backtester(prices)

    # Quick evaluation
    metrics = bt.evaluate_all()
    for detector_name in ["zscore", "benford", "whale_alert", "combined"]:
        m = metrics[detector_name]
        print(f"\n{detector_name.upper()}:")
        print(f"  Precision={m['precision']}, Recall={m['recall']}, F1={m['f1']}")
        print(f"  TP={m['TP']}, FP={m['FP']}, FN={m['FN']}, TN={m['TN']}")

    print(f"\nGround Truth: {metrics['ground_truth_summary']}")

    # Event report
    event_report = bt.event_detection_report()
    print(f"\nEvent Detection Report:")
    print(event_report[["event_name", "detected", "peak_z_score"]].to_string(index=False))
