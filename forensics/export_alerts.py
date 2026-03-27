from __future__ import annotations

from pathlib import Path
from typing import Callable

import pandas as pd


DEFAULT_COLUMNS = [
    "id",
    "marketSlug",
    "detectedAt",
    "eventType",
    "severity",
    "detail",
]


def export_anomalies_to_csv(
    output_path: str | Path,
    slug: str | None = None,
    severity: str | None = None,
) -> pd.DataFrame:
    """Export anomaly alerts to CSV for manual TP/FP verification."""
    query_kwargs: dict[str, str] = {}
    if slug is not None:
        query_kwargs["slug"] = slug
    if severity is not None:
        query_kwargs["severity"] = severity
    try:
        query_func = _resolve_query_func()
        anomalies_df = query_func(**query_kwargs)
    except Exception:
        anomalies_df = pd.DataFrame(columns=DEFAULT_COLUMNS)

    export_df = anomalies_df.copy()
    export_df["is_true_positive"] = ""
    export_df["verification_notes"] = ""

    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    export_df.to_csv(output, index=False)
    return export_df


def _resolve_query_func() -> Callable[..., pd.DataFrame]:
    from core_analysis.db_interface import query_anomalies  # lazy import

    return query_anomalies


if __name__ == "__main__":
    export_anomalies_to_csv("forensics/alerts_to_verify.csv")
