# core_analysis/whale_alert.py
"""
Whale Alert — large trade detection for PolyWatch.

Identifies abnormally large trades (whale activity), cumulative position
build-ups, and directional bias that may signal informed trading or
market manipulation.

Member C — Core Algorithm Module (Phase 3)
"""
import pandas as pd
import numpy as np
from dataclasses import dataclass
from typing import Optional
from datetime import timedelta


@dataclass
class WhaleConfig:
    """Configuration for Whale Alert detector."""
    # Trade size threshold (absolute) to flag as whale trade
    size_threshold: float = 200.0

    # Cumulative volume threshold (within a time window) to flag accumulation
    cumulative_threshold: float = 1000.0

    # Time window (hours) for cumulative / directional analysis
    time_window_hours: int = 24

    # Directional bias: if >X% of volume in a window is one direction → flag
    directional_bias_pct: float = 0.80

    # Severity thresholds based on trade size multiples
    high_severity_multiple: float = 5.0   # >= 5x threshold → high
    medium_severity_multiple: float = 2.0  # >= 2x threshold → medium


class WhaleAlert:
    """
    Whale trade detector.

    Detects:
      - Individual large trades exceeding size threshold
      - Directional bias windows (coordinated buying or selling)
      - Cumulative volume accumulation events

    Usage:
        alert = WhaleAlert()
        whale_trades = alert.detect(trades)
        events = alert.get_anomaly_events(analysis_result, market_slug="slug")
    """

    def __init__(self, config: Optional[WhaleConfig] = None,
                 size_threshold: float = None):
        """
        Args:
            config: WhaleConfig object (preferred)
            size_threshold: Legacy parameter
        """
        if config is not None:
            self.config = config
        else:
            self.config = WhaleConfig()
            if size_threshold is not None:
                self.config.size_threshold = size_threshold

        # Legacy attribute
        self.size_threshold = self.config.size_threshold

    def detect(self, trades: pd.DataFrame) -> pd.DataFrame:
        """
        Detect whale trades from a trades DataFrame.

        Args:
            trades: DataFrame with at least 'trade_size' column.
                    Optionally 'timestamp', 'direction' ('buy'/'sell').

        Returns:
            DataFrame of whale trades (rows exceeding size threshold).
        """
        return trades[trades["trade_size"] >= self.config.size_threshold].copy()

    def analyze(self, trades: pd.DataFrame,
                price_series: pd.Series = None) -> dict:
        """
        Full whale activity analysis.

        Args:
            trades: DataFrame with 'trade_size', optionally 'timestamp', 'direction'
            price_series: Optional price series for context

        Returns:
            {
                whale_trades: DataFrame,
                total_trades, whale_count, whale_pct,
                directional_events: list of bias events,
                summary: dict,
            }
        """
        cfg = self.config
        whale_trades = self.detect(trades)

        total = len(trades)
        n_whale = len(whale_trades)
        whale_pct = round(100.0 * n_whale / total, 2) if total > 0 else 0.0

        # Directional bias analysis
        directional_events = []
        if "timestamp" in trades.columns and "direction" in trades.columns:
            directional_events = self._detect_directional_bias(trades)

        summary = {
            "total_trades": total,
            "whale_trades": n_whale,
            "whale_pct": whale_pct,
            "directional_bias_events": len(directional_events),
            "config": {
                "size_threshold": cfg.size_threshold,
                "cumulative_threshold": cfg.cumulative_threshold,
                "directional_bias_pct": cfg.directional_bias_pct,
            },
        }

        return {
            "whale_trades": whale_trades,
            "directional_events": directional_events,
            "summary": summary,
        }

    def _detect_directional_bias(self, trades: pd.DataFrame) -> list[dict]:
        """
        Detect time windows where trading is heavily directional.

        Returns list of bias event dicts.
        """
        cfg = self.config
        if "timestamp" not in trades.columns or "direction" not in trades.columns:
            return []

        trades_sorted = trades.sort_values("timestamp").copy()
        if trades_sorted.empty:
            return []

        window = timedelta(hours=cfg.time_window_hours)
        events = []
        start_time = trades_sorted["timestamp"].min()
        end_time = trades_sorted["timestamp"].max()

        current = start_time
        while current <= end_time:
            window_end = current + window
            mask = (
                (trades_sorted["timestamp"] >= current) &
                (trades_sorted["timestamp"] < window_end)
            )
            window_trades = trades_sorted[mask]

            if len(window_trades) >= 5:  # Need minimum trades for meaningful analysis
                total_vol = window_trades["trade_size"].sum()
                buy_vol = window_trades.loc[
                    window_trades["direction"] == "buy", "trade_size"
                ].sum()
                sell_vol = total_vol - buy_vol

                buy_pct = buy_vol / total_vol if total_vol > 0 else 0.5

                if buy_pct >= cfg.directional_bias_pct:
                    events.append({
                        "time_start": current,
                        "time_end": window_end,
                        "bias_direction": "buy",
                        "bias_pct": round(float(buy_pct), 4),
                        "total_volume": round(float(total_vol), 2),
                        "n_trades": len(window_trades),
                    })
                elif (1 - buy_pct) >= cfg.directional_bias_pct:
                    events.append({
                        "time_start": current,
                        "time_end": window_end,
                        "bias_direction": "sell",
                        "bias_pct": round(float(1 - buy_pct), 4),
                        "total_volume": round(float(total_vol), 2),
                        "n_trades": len(window_trades),
                    })

            current += timedelta(hours=cfg.time_window_hours // 2 or 1)

        return events

    def get_anomaly_events(self, analysis_result: dict,
                           market_slug: str = "") -> list[dict]:
        """
        Convert whale analysis results to anomaly event dicts
        for db_interface.write_anomaly().
        """
        cfg = self.config
        events = []

        # Whale trade events
        whale_trades = analysis_result.get("whale_trades", pd.DataFrame())
        if not whale_trades.empty:
            for idx, row in whale_trades.iterrows():
                size = float(row["trade_size"])
                multiple = size / cfg.size_threshold if cfg.size_threshold > 0 else 1

                if multiple >= cfg.high_severity_multiple:
                    severity = "high"
                elif multiple >= cfg.medium_severity_multiple:
                    severity = "medium"
                else:
                    severity = "low"

                detected_at = row.get("timestamp", idx)
                events.append({
                    "detected_at": detected_at,
                    "event_type": "whale_trade",
                    "severity": severity,
                    "detail": {
                        "trade_size": round(size, 2),
                        "size_multiple": round(multiple, 2),
                        "direction": row.get("direction", "unknown"),
                        "market_slug": market_slug,
                    },
                })

        # Directional bias events
        for bias in analysis_result.get("directional_events", []):
            events.append({
                "detected_at": bias.get("time_end", bias.get("time_start")),
                "event_type": "whale_directional_bias",
                "severity": "high" if bias.get("bias_pct", 0) >= 0.9 else "medium",
                "detail": {
                    "bias_direction": bias.get("bias_direction"),
                    "bias_pct": bias.get("bias_pct"),
                    "total_volume": bias.get("total_volume"),
                    "n_trades": bias.get("n_trades"),
                    "market_slug": market_slug,
                },
            })

        return events


# ── Convenience Functions ──────────────────────────────────────────────

def simulate_trades_from_prices(price_series: pd.Series,
                                base_volume: float = 50.0,
                                whale_probability: float = 0.03,
                                seed: int = 42) -> pd.DataFrame:
    """
    Generate simulated trade data from a price series.

    When real trade-level data isn't available, this creates realistic
    synthetic trades based on price movements:
      - Larger price changes → larger trade volumes
      - Random whale trades injected at whale_probability rate
      - Direction based on price movement

    Args:
        price_series: Price data with DatetimeIndex
        base_volume: Average trade size
        whale_probability: Probability of a whale trade at each step
        seed: Random seed

    Returns:
        DataFrame with columns: timestamp, trade_size, direction, price
    """
    rng = np.random.RandomState(seed)
    n = len(price_series)
    if n < 2:
        return pd.DataFrame(columns=["timestamp", "trade_size", "direction", "price"])

    returns = price_series.diff().fillna(0)
    abs_returns = returns.abs()

    # Scale volume by return magnitude (larger moves → more activity)
    q75 = abs_returns.quantile(0.75)
    q75 = max(q75, 1e-6)  # avoid division by zero
    return_scale = 1 + (abs_returns / q75).clip(upper=5)

    # Base random volume
    volumes = rng.exponential(scale=base_volume, size=n) * return_scale.values

    # Inject whale trades
    whale_mask = rng.random(n) < whale_probability
    volumes[whale_mask] *= rng.uniform(5, 20, size=whale_mask.sum())

    # Direction: based on price movement + noise
    directions = []
    for i in range(n):
        if returns.iloc[i] > 0:
            directions.append("buy" if rng.random() < 0.7 else "sell")
        elif returns.iloc[i] < 0:
            directions.append("sell" if rng.random() < 0.7 else "buy")
        else:
            directions.append("buy" if rng.random() < 0.5 else "sell")

    trades = pd.DataFrame({
        "timestamp": price_series.index,
        "trade_size": np.round(volumes, 2),
        "direction": directions,
        "price": price_series.values,
    })

    return trades


def run_whale_analysis(trades: pd.DataFrame,
                       price_series: pd.Series = None,
                       config: Optional[WhaleConfig] = None) -> dict:
    """
    One-call convenience function for whale activity analysis.

    Args:
        trades: DataFrame with 'trade_size', optionally 'timestamp', 'direction'
        price_series: Optional price series for context
        config: Optional WhaleConfig

    Returns:
        {
            whale_trades: DataFrame,
            directional_events: list,
            summary: dict,
        }
    """
    alert = WhaleAlert(config=config)
    return alert.analyze(trades, price_series)


if __name__ == "__main__":
    # Demo with synthetic data
    np.random.seed(42)

    # Simple test
    trades = pd.DataFrame({
        "trade_id": range(10),
        "trade_size": [12, 45, 300, 22, 18, 410, 33, 27, 500, 19]
    })

    alert = WhaleAlert(size_threshold=200)
    whales = alert.detect(trades)

    print("Whale trades detected:")
    print(whales)

    # Test with simulated data
    print("\n--- simulate_trades_from_prices ---")
    idx = pd.date_range("2024-01-01", periods=100, freq="h", tz="UTC")
    prices = pd.Series(0.5 + np.cumsum(np.random.normal(0, 0.01, 100)), index=idx)
    sim_trades = simulate_trades_from_prices(prices)
    result = run_whale_analysis(sim_trades, prices)
    print(f"Summary: {result['summary']}")
