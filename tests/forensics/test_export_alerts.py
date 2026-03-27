"""Tests for forensics.export_alerts module."""

from __future__ import annotations

from typing import cast

import pandas as pd
from unittest.mock import patch

from forensics.export_alerts import export_anomalies_to_csv


@patch("forensics.export_alerts._resolve_query_func")
def test_export_anomalies_to_csv(mock_resolve_query_func, tmp_path):
    source_df = pd.DataFrame(
        [
            {
                "id": 1,
                "marketSlug": "presidential-election-winner-2024",
                "detectedAt": "2024-06-28T01:00:00+00:00",
                "eventType": "zscore_spike",
                "severity": "high",
                "detail": {"z_score": 4.2},
            }
        ]
    )
    mock_query = mock_resolve_query_func.return_value
    mock_query.return_value = source_df

    output_csv = tmp_path / "alerts_to_verify.csv"
    exported_df = export_anomalies_to_csv(output_csv)

    mock_query.assert_called_once_with()
    assert output_csv.exists()
    assert "is_true_positive" in exported_df.columns
    assert "verification_notes" in exported_df.columns

    csv_df = cast(pd.DataFrame, pd.read_csv(output_csv))
    assert list(csv_df.columns) == list(exported_df.columns)
    assert len(csv_df) == 1
    assert csv_df.loc[0, "id"] == 1
