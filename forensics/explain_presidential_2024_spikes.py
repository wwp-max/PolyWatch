from __future__ import annotations

import argparse
import csv
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path


DEFAULT_MARKET = "presidential-election-winner-2024"
DEFAULT_THRESHOLD = 0.05
#DEFAULT_CSV = Path(__file__).resolve().parents[1] / "data_pipeline" / "db" / "price_history_seed.csv"
DEFAULT_CSV = Path("data_pipeline") / "db" / "price_history_seed.csv"
DEFAULT_AUDITOR = "CHEN Sijie"


def utc(ts: str) -> datetime:
    normalized = ts.strip().replace("Z", "+00:00")
    if normalized.endswith("+00"):
        normalized = normalized[:-3] + "+00:00"
    return datetime.fromisoformat(normalized).astimezone(timezone.utc)


@dataclass(frozen=True)
class CatalystWindow:
    start: datetime
    end: datetime
    label: str
    reason: str
    confidence: str
    reference_event_time: datetime
    sources: tuple[tuple[str, str], ...]


@dataclass(frozen=True)
class SpikeRecord:
    time: datetime
    price: float
    delta: float
    likely_cause: str
    reason: str
    confidence: str
    reference_event_time: datetime | None
    hours_from_reference_event: float | None


def format_dt(timestamp: datetime) -> str:
    return timestamp.astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")


def human_market_name(slug: str) -> str:
    return slug.replace("-", " ").title()


def build_case_id(slug: str, first_spike: datetime | None) -> str:
    suffix = first_spike.strftime("%Y%m%d") if first_spike is not None else "unknown"
    normalized_slug = slug.upper().replace("-", "_")
    return f"POLYWATCH-{normalized_slug}-{suffix}"


def summarize_confidence(spikes: list[SpikeRecord]) -> str:
    if not spikes:
        return "LOW"
    if all(spike.confidence == "high" for spike in spikes):
        return "HIGH"
    if any(spike.confidence == "low" for spike in spikes):
        return "MEDIUM"
    return "MEDIUM"


CATALYST_WINDOWS = [
    CatalystWindow(
        start=utc("2024-01-04T18:00:00Z"),
        end=utc("2024-01-05T06:00:00Z"),
        label="Ballot-eligibility legal risk repricing",
        reason=(
            "The market was repricing uncertainty around Trump's ballot eligibility."
            " Following the late-2023 Colorado and Maine ballot-removal disputes, traders were still carrying"
            " legal-risk exposure, and many were more willing to sell ahead of a definitive court resolution."
        ),
        confidence="medium",
        reference_event_time=utc("2024-01-05T12:00:00Z"),
        sources=(
            (
                "Timeline of the 2024 United States presidential election: Jan. 5 Supreme Court agrees to hear Trump's Colorado ballot appeal",
                "https://en.wikipedia.org/wiki/Timeline_of_the_2024_United_States_presidential_election",
            ),
            (
                "2024 United States presidential election overview: ballot-access and legal-risk context",
                "https://en.wikipedia.org/wiki/2024_United_States_presidential_election",
            ),
        ),
    ),
    CatalystWindow(
        start=utc("2024-01-07T12:00:00Z"),
        end=utc("2024-01-08T12:00:00Z"),
        label="Pre-Iowa primary momentum rebound",
        reason=(
            "This move looks like a rebound from the earlier legal-risk selloff. With the Iowa caucuses approaching"
            " and Trump still leading the Republican field, the market returned to the core thesis that he was likely"
            " to secure the nomination and enter the general election as the Republican candidate."
        ),
        confidence="medium",
        reference_event_time=utc("2024-01-08T00:00:00Z"),
        sources=(
            (
                "Timeline of the 2024 United States presidential election: January primary calendar and Iowa run-up",
                "https://en.wikipedia.org/wiki/Timeline_of_the_2024_United_States_presidential_election",
            ),
            (
                "2024 United States presidential election overview: Trump led the Republican primary field entering Iowa",
                "https://en.wikipedia.org/wiki/2024_United_States_presidential_election",
            ),
        ),
    ),
    CatalystWindow(
        start=utc("2024-06-27T21:00:00Z"),
        end=utc("2024-06-28T12:00:00Z"),
        label="Biden debate collapse boosted Trump odds",
        reason=(
            "After the June 27 CNN presidential debate, Biden's performance was widely seen as a breakdown, and"
            " Democratic replacement talk intensified almost immediately. In a market pricing whether Trump would win"
            " the 2024 election, that directly increased Trump's implied odds."
        ),
        confidence="high",
        reference_event_time=utc("2024-06-28T01:00:00Z"),
        sources=(
            (
                "2024 United States presidential debates: June 27 CNN debate and immediate fallout",
                "https://en.wikipedia.org/wiki/2024_United_States_presidential_debates",
            ),
            (
                "Timeline of the 2024 United States presidential election: June 27 debate and calls for Biden to suspend campaign",
                "https://en.wikipedia.org/wiki/Timeline_of_the_2024_United_States_presidential_election",
            ),
        ),
    ),
    CatalystWindow(
        start=utc("2024-07-13T22:00:00Z"),
        end=utc("2024-07-14T12:00:00Z"),
        label="Assassination attempt generated sympathy rally",
        reason=(
            "Following the July 13 Pennsylvania rally shooting, the market quickly interpreted the event as"
            " strengthening Trump's sympathy-vote and voter-mobilization dynamics, producing a sharp upward repricing"
            " within a very short time window."
        ),
        confidence="high",
        reference_event_time=utc("2024-07-13T22:11:00Z"),
        sources=(
            (
                "2024 United States presidential election overview: Trump was shot in the ear in an assassination attempt on July 13",
                "https://en.wikipedia.org/wiki/2024_United_States_presidential_election",
            ),
            (
                "Timeline of the 2024 United States presidential election: July 13 rally shooting",
                "https://en.wikipedia.org/wiki/Timeline_of_the_2024_United_States_presidential_election",
            ),
        ),
    ),
    CatalystWindow(
        start=utc("2024-11-06T00:00:00Z"),
        end=utc("2024-11-06T01:30:00Z"),
        label="Election-night early calls favored Trump",
        reason=(
            "Once the first election-night calls came in, with early called states such as Indiana and Kentucky"
            " going to Trump, the market began repricing from a competitive race into a state where Trump was seen"
            " as clearly favored."
        ),
        confidence="high",
        reference_event_time=utc("2024-11-06T00:07:00Z"),
        sources=(
            (
                "Timeline of the 2024 United States presidential election: Nov. 5 election night, first states called for Trump",
                "https://en.wikipedia.org/wiki/Timeline_of_the_2024_United_States_presidential_election",
            ),
            (
                "2024 United States presidential election overview: Trump defeated Harris and swept the swing states",
                "https://en.wikipedia.org/wiki/2024_United_States_presidential_election",
            ),
        ),
    ),
    CatalystWindow(
        start=utc("2024-11-06T02:30:00Z"),
        end=utc("2024-11-06T03:30:00Z"),
        label="Swing-state path increasingly pointed to Trump",
        reason=(
            "As live counting continued in the key battleground states, traders priced in Trump's strengthening path"
            " across the Sun Belt and other swing states. Even if final media calls had not yet arrived, markets"
            " commonly reprice before formal announcements are made."
        ),
        confidence="high",
        reference_event_time=utc("2024-11-06T03:00:00Z"),
        sources=(
            (
                "Timeline of the 2024 United States presidential election: Nov. 6 overnight swing-state progression",
                "https://en.wikipedia.org/wiki/Timeline_of_the_2024_United_States_presidential_election",
            ),
            (
                "2024 United States presidential election overview: Trump won all seven swing states",
                "https://en.wikipedia.org/wiki/2024_United_States_presidential_election",
            ),
        ),
    ),
    CatalystWindow(
        start=utc("2024-11-06T03:30:00Z"),
        end=utc("2024-11-06T04:30:00Z"),
        label="North Carolina call and decisive election-night repricing",
        reason=(
            "North Carolina was called for Trump at roughly 04:18 UTC on November 6, making it the first formally"
            " called major swing state. That signal sharply narrowed the Democratic path and triggered another round"
            " of repricing in Trump's favor."
        ),
        confidence="high",
        reference_event_time=utc("2024-11-06T04:18:00Z"),
        sources=(
            (
                "Timeline of the 2024 United States presidential election: 11:18 PM ET North Carolina called for Trump",
                "https://en.wikipedia.org/wiki/Timeline_of_the_2024_United_States_presidential_election",
            ),
            (
                "2024 United States presidential election overview: Trump victory and Electoral College path",
                "https://en.wikipedia.org/wiki/2024_United_States_presidential_election",
            ),
        ),
    ),
]


def load_market_data(csv_path: Path, slug: str) -> list[tuple[datetime, float]]:
    rows: list[tuple[datetime, float]] = []
    with csv_path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            if row["slug"] != slug:
                continue
            rows.append((utc(row["time"]), float(row["price"])))

    rows.sort(key=lambda item: item[0])
    if not rows:
        raise ValueError(f"No rows found for slug={slug!r} in {csv_path}")
    return rows


def match_catalyst(timestamp: datetime) -> CatalystWindow | None:
    for window in CATALYST_WINDOWS:
        if window.start <= timestamp <= window.end:
            return window
    return None


def find_catalyst_for_spike(spike: SpikeRecord) -> CatalystWindow | None:
    return match_catalyst(spike.time)


def detect_spikes(rows: list[tuple[datetime, float]], threshold: float) -> list[SpikeRecord]:
    spikes: list[SpikeRecord] = []
    previous_price: float | None = None

    for timestamp, price in rows:
        if previous_price is None:
            previous_price = price
            continue

        delta = price - previous_price
        previous_price = price
        if abs(delta) <= threshold:
            continue

        catalyst = match_catalyst(timestamp)
        reference_event_time = catalyst.reference_event_time if catalyst else None
        hours_from_reference_event = None
        if reference_event_time is not None:
            hours_from_reference_event = round(
                (timestamp - reference_event_time).total_seconds() / 3600,
                2,
            )

        spikes.append(
            SpikeRecord(
                time=timestamp,
                price=price,
                delta=delta,
                likely_cause=catalyst.label if catalyst else "No catalyst matched",
                reason=(
                    catalyst.reason
                    if catalyst
                    else "No plausible public catalyst was matched within the predefined event windows."
                ),
                confidence=catalyst.confidence if catalyst else "low",
                reference_event_time=reference_event_time,
                hours_from_reference_event=hours_from_reference_event,
            )
        )

    return spikes


def format_output(spikes: list[SpikeRecord], slug: str, threshold: float) -> str:
    lines = [
        f"Market: {slug}",
        f"Threshold: abs(hourly delta) > {threshold:.2f}",
        f"Spike count: {len(spikes)}",
        "",
    ]

    if not spikes:
        lines.append("No spikes found.")
        return "\n".join(lines)

    for row in spikes:
        lines.append(f"Time: {row.time.isoformat()}")
        lines.append(f"Price: {row.price:.4f}")
        lines.append(f"Delta: {row.delta:+.4f}")
        lines.append(f"Likely cause: {row.likely_cause}")
        lines.append(f"Confidence: {row.confidence}")
        if row.reference_event_time is not None:
            lines.append(
                "Reference event time: "
                f"{row.reference_event_time.isoformat()} "
                f"({row.hours_from_reference_event:+.2f} hours)"
            )
        lines.append(f"Reason: {row.reason}")
        lines.append("")

    return "\n".join(lines).rstrip()


def write_csv(spikes: list[SpikeRecord], path: Path) -> None:
    fieldnames = [
        "time",
        "price",
        "delta",
        "likely_cause",
        "confidence",
        "reference_event_time",
        "hours_from_reference_event",
        "reason",
    ]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for spike in spikes:
            writer.writerow(
                {
                    "time": spike.time.isoformat(),
                    "price": f"{spike.price:.4f}",
                    "delta": f"{spike.delta:+.4f}",
                    "likely_cause": spike.likely_cause,
                    "confidence": spike.confidence,
                    "reference_event_time": (
                        spike.reference_event_time.isoformat() if spike.reference_event_time else ""
                    ),
                    "hours_from_reference_event": (
                        f"{spike.hours_from_reference_event:+.2f}"
                        if spike.hours_from_reference_event is not None
                        else ""
                    ),
                    "reason": spike.reason,
                }
            )


def render_markdown_report(
    spikes: list[SpikeRecord],
    slug: str,
    threshold: float,
    source_csv: Path,
    auditor: str,
) -> str:
    report_date = datetime.now(timezone.utc)
    first_spike = spikes[0].time if spikes else None
    last_spike = spikes[-1].time if spikes else None
    case_id = build_case_id(slug, first_spike)
    severity = summarize_confidence(spikes)
    max_abs_delta = max((abs(spike.delta) for spike in spikes), default=0.0)
    avg_abs_delta = (
        sum(abs(spike.delta) for spike in spikes) / len(spikes)
        if spikes
        else 0.0
    )

    lines = [
        "# PolyWatch Forensic Report",
        "",
        f"**Case ID**: {case_id}  ",
        f"**Auditor**: {auditor}  ",
        f"**Date**: {report_date.strftime('%Y-%m-%d')}  ",
        f"**Severity**: {severity}  ",
        f"**Source Dataset**: `{source_csv}`  ",
        "",
        "> This report is automatically generated from historical price data and a curated public-event timeline. It is an event-attribution report, not a proof of manipulation or causality.",
        "",
        "---",
        "",
        "## 1. Case Summary",
        "",
        "| Field | Value |",
        "|-------|-------|",
        f"| Target Market | {human_market_name(slug)} |",
        f"| Market Slug | `{slug}` |",
        f"| Detection Rule | Absolute hourly price delta > {threshold:.2f} |",
        f"| Spike Count | {len(spikes)} |",
        f"| Time Window | {format_dt(first_spike) if first_spike else 'N/A'} ~ {format_dt(last_spike) if last_spike else 'N/A'} |",
        f"| Largest Absolute Delta | {max_abs_delta:.4f} |",
        f"| Average Absolute Delta | {avg_abs_delta:.4f} |",
        "",
        "---",
        "",
        "## 2. Detection Method",
        "",
        "1. Read hourly price points from the seed CSV.",
        "2. Sort by timestamp and compute point-to-point hourly delta.",
        "3. Flag timestamps where `abs(delta)` exceeds the configured threshold.",
        "4. Match each flagged timestamp against a curated window of public election events.",
        "5. Emit a best-effort explanation with a confidence label.",
        "",
        "---",
        "",
        "## 3. Spike Overview",
        "",
        "| # | Timestamp | Price | Delta | Likely Cause | Confidence |",
        "|---|-----------|-------|-------|--------------|------------|",
    ]

    for index, spike in enumerate(spikes, start=1):
        lines.append(
            f"| {index} | {format_dt(spike.time)} | {spike.price:.4f} | {spike.delta:+.4f} | {spike.likely_cause} | {spike.confidence.upper()} |"
        )

    lines.extend([
        "",
        "---",
        "",
        "## 4. Detailed Findings",
        "",
    ])

    for index, spike in enumerate(spikes, start=1):
        lines.extend([
            f"### 4.{index} Spike at {format_dt(spike.time)}",
            "",
            "| Field | Value |",
            "|-------|-------|",
            f"| Timestamp | {format_dt(spike.time)} |",
            f"| Price | {spike.price:.4f} |",
            f"| Delta | {spike.delta:+.4f} |",
            f"| Likely Cause | {spike.likely_cause} |",
            f"| Confidence | {spike.confidence.upper()} |",
        ])
        if spike.reference_event_time is not None and spike.hours_from_reference_event is not None:
            lines.append(f"| Reference Event Time | {format_dt(spike.reference_event_time)} |")
            lines.append(f"| Time Offset | {spike.hours_from_reference_event:+.2f} hours |")
        lines.extend([
            "",
            "**Assessment**  ",
            spike.reason,
            "",
        ])

    lines.extend([
        "---",
        "",
        "## 5. Conclusion",
        "",
    ])

    if spikes:
        lines.extend([
            f"The market `{slug}` produced {len(spikes)} hourly moves above the configured threshold of {threshold:.2f}.",
            "",
            "Most of the large upward repricings cluster around major public catalysts rather than random isolated prints, especially:",
            "",
            "- The June 27 Biden-Trump debate aftermath",
            "- The July 13 assassination attempt on Trump",
            "- Election-night state calls and swing-state repricing on November 6",
            "",
            "The January spikes are explainable by ballot-eligibility and primary-momentum repricing, but those attributions are weaker than the June, July, and November matches and should be treated as medium-confidence narrative links rather than conclusive evidence.",
        ])
    else:
        lines.append("No spikes exceeded the configured threshold, so no forensic event-attribution findings were generated.")

    lines.extend([
        "",
        "---",
        "",
        "## 6. Referenced Event Sources",
        "",
    ])

    if spikes:
        for index, spike in enumerate(spikes, start=1):
            catalyst = find_catalyst_for_spike(spike)
            lines.extend([
                f"### 6.{index} Sources for Spike at {format_dt(spike.time)}",
                "",
                f"- Spike event: {spike.likely_cause}",
            ])
            if catalyst is None or not catalyst.sources:
                lines.append("- No source list was attached to this catalyst.")
            else:
                for source_title, source_url in catalyst.sources:
                    lines.append(f"- {source_title}: {source_url}")
            lines.append("")
    else:
        lines.append("No referenced event sources were generated because no spikes were detected.")
        lines.append("")

    lines.extend([
        "---",
        "",
        "## 7. Limitations",
        "",
        "- This report uses public event timing and price data only; it does not inspect order-book, wallet, or trade-level data.",
        "- Event matching is window-based and may miss overlapping or slower-moving catalysts.",
        "- A matched event explains plausibility of repricing, not intent or manipulation.",
        "",
    ])

    return "\n".join(lines)


def write_markdown_report(
    spikes: list[SpikeRecord],
    path: Path,
    slug: str,
    threshold: float,
    source_csv: Path,
    auditor: str,
) -> None:
    path.write_text(
        render_markdown_report(spikes, slug, threshold, source_csv, auditor),
        encoding="utf-8",
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Explain large hourly price jumps in the 2024 Trump election market."
    )
    parser.add_argument("--csv", type=Path, default=DEFAULT_CSV)
    parser.add_argument("--slug", default=DEFAULT_MARKET)
    parser.add_argument("--threshold", type=float, default=DEFAULT_THRESHOLD)
    parser.add_argument("--write-csv", type=Path, default=None)
    parser.add_argument("--write-report", type=Path, default=None)
    parser.add_argument("--auditor", default=DEFAULT_AUDITOR)
    args = parser.parse_args()

    rows = load_market_data(args.csv, args.slug)
    spikes = detect_spikes(rows, args.threshold)

    if args.write_csv is not None:
        write_csv(spikes, args.write_csv)

    if args.write_report is not None:
        write_markdown_report(
            spikes,
            args.write_report,
            args.slug,
            args.threshold,
            args.csv,
            args.auditor,
        )

    print(format_output(spikes, args.slug, args.threshold))


if __name__ == "__main__":
    main()