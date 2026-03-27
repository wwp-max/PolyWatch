#!/usr/bin/env python3
# core_analysis/run_analysis.py
"""
PolyWatch Anomaly Detection — Unified Entry Point.

Runs all anomaly detection algorithms (Z-Score, Benford, Whale Alert)
against all active markets in the database, writes results to anomaly_events
table, and optionally runs backtesting.

Usage:
    # Run all detectors on all active markets
    python -m core_analysis.run_analysis

    # Run only Z-Score detector
    python -m core_analysis.run_analysis --detector zscore

    # Run on a specific market
    python -m core_analysis.run_analysis --market presidential-election-winner-2024

    # Run backtest on 2024 election data
    python -m core_analysis.run_analysis --backtest

    # Dry run (don't write to DB)
    python -m core_analysis.run_analysis --dry-run

Member C — Core Algorithm Module (Phase 5)
"""
import argparse
import json
import sys
import os
from datetime import datetime, timezone

import pandas as pd
import numpy as np

# Ensure core_analysis is importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from core_analysis.db_interface import (
    get_price_series, get_active_slugs, get_token_id_by_slug, write_anomaly,
)
from core_analysis.zscore_detector import ZScoreDetector, ZScoreConfig, run_zscore_analysis
from core_analysis.benford_detector import (
    BenfordDetector, BenfordConfig, prepare_price_changes, run_benford_analysis,
)
from core_analysis.whale_alert import (
    WhaleAlert, WhaleConfig, simulate_trades_from_prices, run_whale_analysis,
)
from core_analysis.backtester import Backtester, run_backtest


# ══════════════════════════════════════════════════════════════════════
#  Per-Market Analysis
# ══════════════════════════════════════════════════════════════════════

def analyze_market(slug: str, detectors: list[str] = None,
                   dry_run: bool = False, verbose: bool = True) -> dict:
    """
    Run selected detectors on a single market.

    Args:
        slug: Market slug
        detectors: List of detector names to run ("zscore", "benford", "whale")
                   Defaults to all.
        dry_run: If True, don't write results to database
        verbose: Print progress

    Returns:
        Dict with results per detector
    """
    if detectors is None:
        detectors = ["zscore", "benford", "whale"]

    if verbose:
        print(f"\n{'='*60}")
        print(f"  Market: {slug}")
        print(f"{'='*60}")

    # Fetch price data
    price_df = get_price_series(slug)
    if price_df.empty:
        if verbose:
            print(f"  [SKIP] No price data for {slug}")
        return {"slug": slug, "error": "no data"}

    price_series = price_df["price"]
    if verbose:
        print(f"  Data points: {len(price_series)}")
        print(f"  Time range: {price_series.index[0]} ~ {price_series.index[-1]}")

    token_id = get_token_id_by_slug(slug)
    results = {"slug": slug, "data_points": len(price_series)}

    # ── Z-Score ────────────────────────────────────────────────────
    if "zscore" in detectors:
        if verbose:
            print(f"\n  [Z-Score] Running...")
        try:
            zscore_result = run_zscore_analysis(price_series)
            summary = zscore_result["summary"]
            events = zscore_result["events"]

            if verbose:
                print(f"  [Z-Score] Anomalies: {summary['anomaly_points']} "
                      f"({summary['anomaly_rate']}%)")
                print(f"  [Z-Score] High severity: {summary['high_severity']}, "
                      f"Clusters: {summary['clusters']}")

            # Write to DB
            if not dry_run and token_id:
                n_written = _write_events_to_db(token_id, events, verbose)
                results["zscore_written"] = n_written

            results["zscore"] = summary
        except Exception as e:
            if verbose:
                print(f"  [Z-Score] ERROR: {e}")
            results["zscore_error"] = str(e)

    # ── Benford ────────────────────────────────────────────────────
    if "benford" in detectors:
        if verbose:
            print(f"\n  [Benford] Running...")
        try:
            price_changes = prepare_price_changes(price_series)
            benford_result = run_benford_analysis(price_changes)
            summary = benford_result["summary"]
            n_anomaly_windows = len(benford_result.get("anomaly_windows", []))

            if verbose:
                print(f"  [Benford] Conforming: {summary['overall_conforming']}")
                print(f"  [Benford] MAD: {summary['mad']}, "
                      f"Level: {summary['conformity_level']}")
                print(f"  [Benford] Anomaly windows: {n_anomaly_windows}")

            # Write to DB
            if not dry_run and token_id:
                detector = BenfordDetector()
                events = detector.get_anomaly_events(
                    benford_result.get("window_results", []), market_slug=slug
                )
                n_written = _write_events_to_db(token_id, events, verbose)
                results["benford_written"] = n_written

            results["benford"] = summary
            results["benford"]["anomaly_windows"] = n_anomaly_windows
        except Exception as e:
            if verbose:
                print(f"  [Benford] ERROR: {e}")
            results["benford_error"] = str(e)

    # ── Whale Alert ────────────────────────────────────────────────
    if "whale" in detectors:
        if verbose:
            print(f"\n  [Whale Alert] Running (simulated trades)...")
        try:
            trades = simulate_trades_from_prices(price_series)
            whale_result = run_whale_analysis(trades, price_series)
            summary = whale_result["summary"]

            if verbose:
                print(f"  [Whale Alert] Total trades: {summary['total_trades']}")
                print(f"  [Whale Alert] Whale trades: {summary['whale_trades']} "
                      f"({summary['whale_pct']}%)")
                print(f"  [Whale Alert] Directional bias events: "
                      f"{summary['directional_bias_events']}")

            # Write to DB
            if not dry_run and token_id:
                alert = WhaleAlert()
                events = alert.get_anomaly_events(whale_result, market_slug=slug)
                n_written = _write_events_to_db(token_id, events, verbose)
                results["whale_written"] = n_written

            results["whale_alert"] = summary
        except Exception as e:
            if verbose:
                print(f"  [Whale Alert] ERROR: {e}")
            results["whale_error"] = str(e)

    return results


def _write_events_to_db(token_id: str, events: list[dict],
                        verbose: bool = True) -> int:
    """Write anomaly events to database. Returns count written."""
    written = 0
    for event in events:
        try:
            detected_at = event.get("detected_at")
            if detected_at is None:
                continue
            write_anomaly(
                token_id=token_id,
                detected_at=detected_at,
                event_type=event["event_type"],
                severity=event["severity"],
                detail=event.get("detail", {}),
            )
            written += 1
        except Exception as e:
            if verbose:
                print(f"    [DB] Write failed: {e}")
    if verbose and written > 0:
        print(f"    [DB] Wrote {written} anomaly events")
    return written


# ══════════════════════════════════════════════════════════════════════
#  Backtest Mode
# ══════════════════════════════════════════════════════════════════════

def run_backtest_mode(verbose: bool = True) -> dict:
    """
    Run full backtest on the 2024 US election data.
    """
    slug = "presidential-election-winner-2024"
    if verbose:
        print(f"\n{'='*60}")
        print(f"  BACKTEST MODE: {slug}")
        print(f"{'='*60}")

    price_df = get_price_series(slug)
    if price_df.empty:
        print(f"  [ERROR] No data for {slug}")
        return {"error": "no data"}

    price_series = price_df["price"]
    if verbose:
        print(f"  Data points: {len(price_series)}")

    bt = Backtester(price_series)

    if verbose:
        print(f"  Ground truth positives: {int(bt.ground_truth.sum())} / {len(bt.ground_truth)}")
        print(f"\n  Running all detectors...")

    report = bt.generate_report()

    # Print results
    if verbose:
        print(f"\n  {'─'*50}")
        print(f"  RESULTS:")
        print(f"  {'─'*50}")

        for name in ["zscore", "benford", "whale_alert", "combined"]:
            m = report["all_metrics"][name]
            print(f"\n  {name.upper()}:")
            print(f"    Precision: {m['precision']:.4f}")
            print(f"    Recall:    {m['recall']:.4f}")
            print(f"    F1:        {m['f1']:.4f}")
            print(f"    TP={m['TP']}, FP={m['FP']}, FN={m['FN']}, TN={m['TN']}")

        print(f"\n  Event Detection:")
        event_df = report["event_report"]
        for _, row in event_df.iterrows():
            status = "DETECTED" if row["detected"] else "MISSED"
            print(f"    [{status}] {row['event_name']} ({row['event_date']}) "
                  f"peak_z={row['peak_z_score']}")

        if not report["grid_search_top5"].empty:
            print(f"\n  Top 5 Z-Score Configs (by F1):")
            top5 = report["grid_search_top5"]
            for i, row in top5.iterrows():
                print(f"    #{i+1}: z_thresh={row.get('z_threshold')}, "
                      f"short_w={row.get('short_window')}, "
                      f"F1={row.get('f1', 'N/A')}")

    return report


# ══════════════════════════════════════════════════════════════════════
#  CLI
# ══════════════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(
        description="PolyWatch Anomaly Detection Engine — Member C",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python -m core_analysis.run_analysis                     # Run all on all markets
  python -m core_analysis.run_analysis --detector zscore   # Z-Score only
  python -m core_analysis.run_analysis --market slug-name  # Specific market
  python -m core_analysis.run_analysis --backtest          # Run backtest
  python -m core_analysis.run_analysis --dry-run           # Don't write to DB
        """,
    )
    parser.add_argument(
        "--market", "-m", type=str, default=None,
        help="Specific market slug to analyze (default: all active markets)",
    )
    parser.add_argument(
        "--detector", "-d", type=str, nargs="+",
        choices=["zscore", "benford", "whale"],
        default=None,
        help="Detectors to run (default: all)",
    )
    parser.add_argument(
        "--backtest", action="store_true",
        help="Run backtesting on 2024 election data",
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Don't write results to database",
    )
    parser.add_argument(
        "--output", "-o", type=str, default=None,
        help="Output results to JSON file",
    )
    parser.add_argument(
        "--quiet", "-q", action="store_true",
        help="Suppress verbose output",
    )

    args = parser.parse_args()
    verbose = not args.quiet

    if verbose:
        print("╔══════════════════════════════════════════════════╗")
        print("║   PolyWatch Anomaly Detection Engine v1.0       ║")
        print("║   Member C — Core Algorithm Module              ║")
        print("╚══════════════════════════════════════════════════╝")

    all_results = {}

    # Backtest mode
    if args.backtest:
        report = run_backtest_mode(verbose)
        all_results["backtest"] = _serialize_report(report)
    else:
        # Normal analysis mode
        if args.market:
            slugs = [args.market]
        else:
            try:
                slugs = get_active_slugs()
                if verbose:
                    print(f"\nFound {len(slugs)} active markets")
            except Exception as e:
                print(f"[ERROR] Cannot connect to database: {e}")
                print("Make sure the PolyWatch database is running (docker-compose up)")
                sys.exit(1)

        for slug in slugs:
            result = analyze_market(
                slug,
                detectors=args.detector,
                dry_run=args.dry_run,
                verbose=verbose,
            )
            all_results[slug] = result

    # Output to file
    if args.output:
        with open(args.output, "w") as f:
            json.dump(all_results, f, indent=2, default=str)
        if verbose:
            print(f"\nResults written to {args.output}")

    if verbose:
        print(f"\nDone. Analyzed {len(all_results)} market(s).")


def _serialize_report(report: dict) -> dict:
    """Convert report to JSON-serializable format."""
    serialized = {}
    for key, value in report.items():
        if isinstance(value, pd.DataFrame):
            serialized[key] = value.to_dict(orient="records")
        elif isinstance(value, dict):
            serialized[key] = _serialize_report(value)
        elif isinstance(value, (np.integer, np.floating)):
            serialized[key] = float(value)
        else:
            serialized[key] = value
    return serialized


if __name__ == "__main__":
    main()
