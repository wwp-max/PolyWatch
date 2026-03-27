from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any, cast

import pandas as pd


TRUE_LABELS = {"true", "1", "yes", "y", "tp", "true_positive"}
FALSE_LABELS = {"false", "0", "no", "n", "fp", "false_positive"}


def _normalize_label(value: Any) -> str:
    if value is None:
        return ""
    text = str(value).strip()
    if text == "" or text.lower() == "nan":
        return ""
    return text.lower()


def generate_report(
    input_csv: str | Path, output_md: str | Path
) -> dict[str, float | int]:
    """Generate false-positive markdown report from manually labeled anomalies."""
    input_path = Path(input_csv)
    output_path = Path(output_md)

    df = cast(pd.DataFrame, pd.read_csv(input_path))
    records = cast(list[dict[str, Any]], df.to_dict(orient="records"))
    labels = [_normalize_label(record.get("is_true_positive")) for record in records]

    total_alerts = len(records)
    true_positives = sum(1 for label in labels if label in TRUE_LABELS)
    false_positives = sum(1 for label in labels if label in FALSE_LABELS)
    labeled_alerts = true_positives + false_positives
    fp_rate = (false_positives / total_alerts) if total_alerts else 0.0

    lines = [
        "# PolyWatch v0.1 False Positive Report",
        "",
        f"Generated at (UTC): {datetime.now(timezone.utc).isoformat()}",
        "",
        "## Summary",
        "",
        f"- Total alerts: **{total_alerts}**",
        f"- Labeled alerts (TP/FP): **{labeled_alerts}**",
        f"- True positives: **{true_positives}**",
        f"- False positives: **{false_positives}**",
        f"- False Positive Rate (FP / Total): **{fp_rate:.2%}**",
        "",
        "## Notes",
        "",
        "- FP rate is computed as `false_positives / total_alerts`.",
        "- Unlabeled rows are included in total alerts but excluded from TP/FP counts.",
    ]

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    return {
        "total_alerts": total_alerts,
        "labeled_alerts": labeled_alerts,
        "true_positives": true_positives,
        "false_positives": false_positives,
        "fp_rate": fp_rate,
    }
