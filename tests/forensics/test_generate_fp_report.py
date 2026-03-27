"""Tests for forensics.generate_fp_report module."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from forensics.generate_fp_report import generate_report


def test_generate_report(tmp_path: Path) -> None:
    input_csv = tmp_path / "labeled_alerts.csv"
    output_md = tmp_path / "v0.1_false_positive_report.md"

    mock_df = pd.DataFrame(
        [
            {"id": 1, "is_true_positive": "true", "verification_notes": "organic"},
            {"id": 2, "is_true_positive": "false", "verification_notes": "news-driven"},
            {"id": 3, "is_true_positive": "fp", "verification_notes": "debate event"},
            {
                "id": 4,
                "is_true_positive": "tp",
                "verification_notes": "suspicious pattern",
            },
            {"id": 5, "is_true_positive": "", "verification_notes": "pending"},
        ]
    )
    mock_df.to_csv(input_csv, index=False)

    stats = generate_report(input_csv=input_csv, output_md=output_md)

    assert output_md.exists()
    assert stats["total_alerts"] == 5
    assert stats["true_positives"] == 2
    assert stats["false_positives"] == 2
    assert abs(float(stats["fp_rate"]) - 0.4) < 1e-9

    content = output_md.read_text(encoding="utf-8")
    assert "# PolyWatch v0.1 False Positive Report" in content
    assert "- Total alerts: **5**" in content
    assert "- False positives: **2**" in content
    assert "- False Positive Rate (FP / Total): **40.00%**" in content
