# Milestone 2 & 3 Forensics Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build the verification pipeline to export alerts and calculate False Positive Rates (Milestone 2), and build the GraphViz fund flow visualization to generate deep case studies (Milestone 3).

**Architecture:** We will create Python scripts inside the `forensics` module that interface with the existing PostgreSQL database (via `core_analysis.db_interface`) to export anomalies. Then, we will create report generators that read labeled data to calculate False Positive rates. Finally, we will integrate `graphviz` to generate wallet funding graphs for the final case studies.

**Tech Stack:** Python 3, Pandas, Graphviz, Pytest, unittest.mock

---

### Task 1: Milestone 2 - Alert Verification Exporter

**Files:**
- Create: `forensics/export_alerts.py`
- Test: `tests/forensics/test_export_alerts.py`

**Step 1: Write the failing test**

```python
# tests/forensics/test_export_alerts.py
import os
import pandas as pd
from unittest.mock import patch
from forensics.export_alerts import export_anomalies_to_csv

@patch("forensics.export_alerts.query_anomalies")
def test_export_anomalies_to_csv(mock_query, tmp_path):
    # Setup mock dataframe
    mock_df = pd.DataFrame({
        "id": [1, 2],
        "marketSlug": ["market-1", "market-2"],
        "detectedAt": ["2026-01-01", "2026-01-02"],
        "eventType": ["spike", "whale"],
        "severity": ["high", "medium"],
        "detail": ["{}", "{}"]
    })
    mock_query.return_value = mock_df
    
    output_file = tmp_path / "alerts.csv"
    export_anomalies_to_csv(str(output_file))
    
    assert os.path.exists(output_file)
    df_out = pd.read_csv(output_file)
    assert "is_true_positive" in df_out.columns
    assert "verification_notes" in df_out.columns
    assert len(df_out) == 2
```

**Step 2: Run test to verify it fails**

Run: `python -m pytest tests/forensics/test_export_alerts.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'forensics.export_alerts'`

**Step 3: Write minimal implementation**

```python
# forensics/export_alerts.py
import pandas as pd
from core_analysis.db_interface import query_anomalies

def export_anomalies_to_csv(output_path: str):
    df = query_anomalies()
    if df.empty:
        df = pd.DataFrame(columns=["id", "marketSlug", "detectedAt", "eventType", "severity", "detail"])
    
    # Add empty columns for manual labeling
    df["is_true_positive"] = ""
    df["verification_notes"] = ""
    
    df.to_csv(output_path, index=False)
    print(f"Exported {len(df)} anomalies to {output_path} for verification.")

if __name__ == "__main__":
    export_anomalies_to_csv("forensics/alerts_to_verify.csv")
```

**Step 4: Run test to verify it passes**

Run: `python -m pytest tests/forensics/test_export_alerts.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add tests/forensics/test_export_alerts.py forensics/export_alerts.py
git commit -m "feat(forensics): add alert exporter for manual verification (Milestone 2)"
```

---

### Task 2: Milestone 2 - False Positive Report Generator

**Files:**
- Create: `forensics/generate_fp_report.py`
- Test: `tests/forensics/test_generate_fp_report.py`

**Step 1: Write the failing test**

```python
# tests/forensics/test_generate_fp_report.py
import os
import pandas as pd
from forensics.generate_fp_report import generate_report

def test_generate_report(tmp_path):
    # Create fake verified data
    csv_file = tmp_path / "alerts.csv"
    df = pd.DataFrame({
        "id": [1, 2, 3, 4],
        "marketSlug": ["m1", "m1", "m2", "m2"],
        "is_true_positive": ["TRUE", "FALSE", "FALSE", ""] # 1 TP, 2 FP, 1 unverified
    })
    df.to_csv(csv_file, index=False)
    
    out_md = tmp_path / "report.md"
    stats = generate_report(str(csv_file), str(out_md))
    
    assert stats["total"] == 4
    assert stats["verified"] == 3
    assert stats["tp"] == 1
    assert stats["fp"] == 2
    assert stats["fp_rate"] == 2/3
    assert os.path.exists(out_md)
    
    with open(out_md, "r", encoding="utf-8") as f:
        content = f.read()
        assert "False Positive Rate: 66.67%" in content
```

**Step 2: Run test to verify it fails**

Run: `python -m pytest tests/forensics/test_generate_fp_report.py -v`
Expected: FAIL with `ModuleNotFoundError`

**Step 3: Write minimal implementation**

```python
# forensics/generate_fp_report.py
import pandas as pd

def generate_report(input_csv: str, output_md: str) -> dict:
    df = pd.read_csv(input_csv)
    total = len(df)
    
    # Filter only rows that have been labeled
    df["is_true_positive"] = df["is_true_positive"].astype(str).str.strip().str.upper()
    verified_df = df[df["is_true_positive"].isin(["TRUE", "FALSE"])]
    
    verified_count = len(verified_df)
    if verified_count == 0:
        return {"total": total, "verified": 0, "tp": 0, "fp": 0, "fp_rate": 0.0}
        
    tp_count = len(verified_df[verified_df["is_true_positive"] == "TRUE"])
    fp_count = len(verified_df[verified_df["is_true_positive"] == "FALSE"])
    fp_rate = fp_count / verified_count
    
    stats = {
        "total": total,
        "verified": verified_count,
        "tp": tp_count,
        "fp": fp_count,
        "fp_rate": fp_rate
    }
    
    md_content = f"""# PolyWatch v0.1 False Positive Report

## Summary Statistics
- **Total Alerts**: {stats['total']}
- **Verified Alerts**: {stats['verified']}
- **True Positives (TP)**: {stats['tp']}
- **False Positives (FP)**: {stats['fp']}
- **False Positive Rate**: {stats['fp_rate']:.2%}

## Recommendations
- The False Positive rate is {stats['fp_rate']:.2%}. 
- Consider adjusting the detection threshold in `zscore_detector.py` or implementing a news-event filter.
"""
    with open(output_md, "w", encoding="utf-8") as f:
        f.write(md_content)
        
    return stats

if __name__ == "__main__":
    generate_report("forensics/alerts_to_verify.csv", "forensics/v0.1_false_positive_report.md")
```

**Step 4: Run test to verify it passes**

Run: `python -m pytest tests/forensics/test_generate_fp_report.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add tests/forensics/test_generate_fp_report.py forensics/generate_fp_report.py
git commit -m "feat(forensics): generate FP rate markdown report from labeled CSV (Milestone 2)"
```

---

### Task 3: Milestone 3 - Setup GraphViz Dependency

**Files:**
- Modify: `requirements.txt`

**Step 1: Add dependency to requirements**

```bash
echo "graphviz" >> requirements.txt
pip install -r requirements.txt
```

**Step 2: Commit**

```bash
git add requirements.txt
git commit -m "chore(deps): add graphviz for fund flow visualization"
```

---

### Task 4: Milestone 3 - Fund Flow Graph Generator

**Files:**
- Create: `forensics/fund_flow_graph.py`
- Test: `tests/forensics/test_fund_flow_graph.py`

**Step 1: Write the failing test**

```python
# tests/forensics/test_fund_flow_graph.py
import os
from forensics.fund_flow_graph import create_wallet_graph

def test_create_wallet_graph(tmp_path):
    edges = [
        ("Tornado Cash", "Wallet A", "500K USDC"),
        ("Wallet A", "Wallet B", "100K USDC"),
        ("Wallet A", "Wallet C", "100K USDC")
    ]
    out_prefix = str(tmp_path / "fund_flow")
    
    # generate returns the path to the dot source or rendered file
    dot_file = create_wallet_graph(edges, out_prefix)
    
    assert os.path.exists(dot_file)
    with open(dot_file, "r") as f:
        content = f.read()
        assert "Tornado Cash" in content
        assert "Wallet B" in content
        assert "500K USDC" in content
```

**Step 2: Run test to verify it fails**

Run: `python -m pytest tests/forensics/test_fund_flow_graph.py -v`
Expected: FAIL with `ModuleNotFoundError`

**Step 3: Write minimal implementation**

```python
# forensics/fund_flow_graph.py
import graphviz

def create_wallet_graph(edges: list[tuple], output_prefix: str) -> str:
    """
    Creates a GraphViz directed graph from a list of edges.
    Edges format: [(source, target, label), ...]
    """
    dot = graphviz.Digraph(comment='Fund Flow Analysis', format='png')
    dot.attr(rankdir='TB', size='8,8')
    
    # To keep track of added nodes
    nodes = set()
    
    for src, dst, label in edges:
        if src not in nodes:
            dot.node(src, src, shape='box', style='filled', fillcolor='lightgrey')
            nodes.add(src)
        if dst not in nodes:
            dot.node(dst, dst, shape='box')
            nodes.add(dst)
            
        dot.edge(src, dst, label=label)
        
    dot.save(output_prefix + ".dot")
    try:
        dot.render(output_prefix, cleanup=False)
    except graphviz.backend.execute.ExecutableNotFound:
        # Graceful degradation if Graphviz binary is not installed on OS
        print("Graphviz executable not found. Generated .dot file only.")
        
    return output_prefix + ".dot"

if __name__ == "__main__":
    sample_edges = [
        ("Tornado Cash", "Wallet 0x1a2b", "500k USDC"),
        ("Wallet 0x1a2b", "Wallet 0x2b3c", "100k USDC"),
        ("Wallet 0x1a2b", "Wallet 0x3c4d", "100k USDC"),
        ("Wallet 0x2b3c", "Polymarket CLOB", "100k Buy"),
        ("Wallet 0x3c4d", "Polymarket CLOB", "100k Buy")
    ]
    create_wallet_graph(sample_edges, "forensics/sample_fund_flow")
```

**Step 4: Run test to verify it passes**

Run: `python -m pytest tests/forensics/test_fund_flow_graph.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add tests/forensics/test_fund_flow_graph.py forensics/fund_flow_graph.py
git commit -m "feat(forensics): add graphviz fund flow visualizer (Milestone 3)"
```

---

### Task 5: Milestone 3 - Individual Evidence Pack Finalization

**Files:**
- Create/Update: `forensics/Individual-Evidence-Pack-Milestone3.md`
- Reference artifacts from: `forensics/alerts_to_verify.csv`, `forensics/v0.1_false_positive_report.md`, `forensics/case_study_001.md`, `forensics/case_study_002.md`, `forensics/case_study_003.md`, `forensics/case_00X_fund_flow.dot/.png`

> **De-duplication rule**: This task is packaging/indexing only. Do NOT rewrite detailed case analysis, transaction tables, or timeline reasoning already present in `case_study_00X.md` or other source artifacts.

**Step 1: Build submission structure**

Add sections in `forensics/Individual-Evidence-Pack-Milestone3.md`:

1. Milestone 2 evidence summary
2. Milestone 3 case-study evidence summary
3. Transaction hash table and timestamp synchronization table
4. Confidence and decision rationale
5. Final submission checklist

**Step 2: Fill evidence links and tables**

- Link generated artifacts in `forensics/`
- Add artifact-status mapping table (artifact path, purpose, completeness, notes)
- Ensure TP/FP reasoning references remain consistent with `v0.1_false_positive_report.md` and `case_study_00X.md`

**Step 3: Verification**

Run:

`python -m pytest tests/forensics/test_export_alerts.py tests/forensics/test_generate_fp_report.py tests/forensics/test_fund_flow_graph.py -v`

Expected: PASS

**Step 4: Final readiness check**

- Confirm every referenced path exists
- Confirm Evidence Pack has no missing critical section
- Confirm instructor submission requirements are explicitly addressed in the pack
