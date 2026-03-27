# core_analysis/data_quality.py
"""
Data Quality Report generator for PolyWatch pipeline.
Analyzes completeness, consistency, and timeliness of price data.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

from datetime import datetime, timezone, timedelta

from db_interface import get_market_stats, get_price_series, get_data_gaps, get_all_markets_meta


# Health thresholds
COMPLETENESS_HEALTHY = 95.0     # >= 95% = healthy
COMPLETENESS_DEGRADED = 85.0    # >= 85% = degraded, else critical
LATEST_AGE_HEALTHY = 2          # hours, for active markets
LATEST_AGE_DEGRADED = 12        # hours


def analyze_market(slug: str, question: str, row_count: int,
                   first_time, last_time, avg_price) -> dict:
    """Analyze a single market's data quality."""
    result = {
        "slug": slug,
        "question": question,
        "row_count": row_count,
        "time_range": {
            "start": first_time.isoformat() if first_time else None,
            "end": last_time.isoformat() if last_time else None,
        },
        "avg_price": float(avg_price) if avg_price else None,
        "completeness_pct": 0.0,
        "max_gap_hours": 0,
        "out_of_range_prices": 0,
        "latest_age_hours": None,
        "health": "unknown",
        "notes": [],
    }

    if row_count == 0:
        result["health"] = "no_data"
        result["notes"].append("No price data in database")
        return result

    # Completeness
    if first_time and last_time:
        span_hours = (last_time - first_time).total_seconds() / 3600
        if span_hours > 0:
            expected_points = max(span_hours, 1)
            completeness = min(row_count / expected_points * 100, 100.0)
            result["completeness_pct"] = round(completeness, 1)
        else:
            result["completeness_pct"] = 100.0

    # Data gaps
    try:
        gaps = get_data_gaps(slug)
        if gaps:
            result["max_gap_hours"] = max(g["gap_hours"] for g in gaps)
            result["notes"].append(f"{len(gaps)} gap(s) found, max {result['max_gap_hours']}h")
    except Exception:
        pass

    # Out-of-range prices
    try:
        df = get_price_series(slug)
        if not df.empty:
            oor = ((df["price"] < 0.0) | (df["price"] > 1.0)).sum()
            result["out_of_range_prices"] = int(oor)
            if oor > 0:
                result["notes"].append(f"{oor} price(s) outside [0.0, 1.0]")
    except Exception:
        pass

    # Latest age
    if last_time:
        now = datetime.now(timezone.utc)
        if last_time.tzinfo is None:
            last_time = last_time.replace(tzinfo=timezone.utc)
        age_hours = (now - last_time).total_seconds() / 3600
        result["latest_age_hours"] = round(age_hours, 1)

    # Health classification
    if result["latest_age_hours"] and result["latest_age_hours"] > 90 * 24:
        result["health"] = "closed"
        result["notes"].append("Market closed (no data for >90 days)")
    elif result["out_of_range_prices"] > 0:
        result["health"] = "critical"
        result["notes"].append("Contains out-of-range price values")
    elif result["completeness_pct"] < COMPLETENESS_DEGRADED:
        result["health"] = "critical"
        result["notes"].append(f"Completeness {result['completeness_pct']}% < {COMPLETENESS_DEGRADED}%")
    elif result["completeness_pct"] < COMPLETENESS_HEALTHY:
        result["health"] = "degraded"
        result["notes"].append(f"Completeness {result['completeness_pct']}% < {COMPLETENESS_HEALTHY}%")
    elif (result["latest_age_hours"] is not None
          and result["latest_age_hours"] > LATEST_AGE_DEGRADED):
        result["health"] = "degraded"
        result["notes"].append(f"Latest data is {result['latest_age_hours']}h old")
    else:
        result["health"] = "healthy"

    if not result["notes"]:
        result["notes"].append("OK")

    return result


def generate_report() -> dict:
    """Generate complete data quality report."""
    stats = get_market_stats()
    all_meta = get_all_markets_meta()
    meta_slugs = {m["slug"] for m in all_meta}
    stat_slugs = {s["slug"] for s in stats if s["row_count"] > 0}

    orphan_slugs = meta_slugs - stat_slugs
    orphan_markets = [m for m in all_meta if m["slug"] in orphan_slugs]

    market_results = []
    for s in stats:
        market_results.append(analyze_market(
            slug=s["slug"],
            question=s["question"] or "",
            row_count=s["row_count"],
            first_time=s["first_time"],
            last_time=s["last_time"],
            avg_price=s["avg_price"],
        ))

    total_rows = sum(s["row_count"] for s in stats)
    active_markets = sum(1 for r in market_results if r["health"] in ("healthy", "degraded", "critical"))

    healths = [r["health"] for r in market_results if r["row_count"] > 0]
    if any(h == "critical" for h in healths):
        overall = "critical"
    elif any(h == "degraded" for h in healths):
        overall = "degraded"
    else:
        overall = "healthy"

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "summary": {
            "total_markets": len(market_results),
            "active_markets": active_markets,
            "total_rows": total_rows,
            "orphan_markets": len(orphan_markets),
            "overall_health": overall,
        },
        "markets": market_results,
        "orphan_markets": [
            {"slug": m["slug"], "question": m["question"]} for m in orphan_markets
        ],
    }


def format_markdown(report: dict) -> str:
    """Format report as human-readable markdown."""
    s = report["summary"]

    health_icon = {"healthy": "HEALTHY", "degraded": "DEGRADED", "critical": "CRITICAL"}

    lines = [
        f"# PolyWatch Data Quality Report",
        f"",
        f"**Date:** {report['generated_at'][:10]}  ",
        f"**Health:** {health_icon.get(s['overall_health'], s['overall_health'])}  ",
        f"**Total Rows:** {s['total_rows']:,}  ",
        f"**Markets:** {s['total_markets']} ({s['active_markets']} with data)  ",
        f"**Orphan Markets:** {s['orphan_markets']} (metadata only, no price data)",
        f"",
        f"## Market Details",
        f"",
        f"| Market | Rows | Completeness | Max Gap | Health | Notes |",
        f"|--------|------|-------------|---------|--------|-------|",
    ]

    for m in report["markets"]:
        slug = m["slug"][:40]
        rows = f"{m['row_count']:,}"
        comp = f"{m['completeness_pct']:.1f}%"
        gap = f"{m['max_gap_hours']:.0f}h" if m["max_gap_hours"] > 0 else "-"
        h = m["health"]
        notes = "; ".join(m["notes"])[:50]
        lines.append(f"| {slug} | {rows} | {comp} | {gap} | {h} | {notes} |")

    if report["orphan_markets"]:
        lines.append("")
        lines.append("## Orphan Markets (no price data)")
        lines.append("")
        for o in report["orphan_markets"]:
            lines.append(f"- `{o['slug']}` — {o['question']}")

    lines.append("")
    lines.append("---")
    lines.append("*Generated by PolyWatch data_quality.py*")
    return "\n".join(lines)
