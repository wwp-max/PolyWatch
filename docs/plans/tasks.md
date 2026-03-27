# Tasks: Milestone 2 & 3 Forensics Implementation

**Input**: 
- `/specs/001-milestone2-validation/spec.md`
- `/specs/002-milestone3-investigation/spec.md`
- `/docs/plans/2026-03-27-milestone3-spec.md`

**Prerequisites**: plan.md, spec.md

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

---

## 1. Setup & Dependencies

- [x] `[T1.1]` `[P]` `[US-Setup]` Ensure Member-D forensics dependencies (`pandas`, `graphviz`, `psycopg2-binary`) are included in root `requirements.txt`.
- [x] `[T1.2]` `[P]` `[US-Setup]` Create placeholder `tests/forensics/test_export_alerts.py`, `tests/forensics/test_generate_fp_report.py`, and `tests/forensics/test_fund_flow_graph.py` files.

## 2. Milestone 2: Alert Verification (M2-US1, M2-US2)

**User Story**: Retrieve Alert History & Manual Verification

- [x] `[T2.1]` `[ ]` `[M2-US1]` Implement `test_export_anomalies_to_csv` in `tests/forensics/test_export_alerts.py` using `unittest.mock.patch`.
- [x] `[T2.2]` `[ ]` `[M2-US1]` Implement `export_anomalies_to_csv` in `forensics/export_alerts.py` to fetch from DB and add `is_true_positive` and `verification_notes` columns.
- [x] `[T2.3]` `[ ]` `[M2-US1]` Ensure `python -m pytest tests/forensics/test_export_alerts.py -v` passes.
- [x] `[T2.4]` `[ ]` `[M2-US2]` Execute `export_anomalies_to_csv("forensics/alerts_to_verify.csv")` to generate the initial blank verification file.

## 3. Milestone 2: False Positive Reporting (M2-US3)

**User Story**: False Positive Feedback Report

- [x] `[T3.1]` `[P]` `[M2-US3]` Implement `test_generate_report` in `tests/forensics/test_generate_fp_report.py` with mock CSV data containing TP/FP labeled rows.
- [x] `[T3.2]` `[ ]` `[M2-US3]` Implement `generate_report(input_csv, output_md)` in `forensics/generate_fp_report.py` to calculate FP rate and output Markdown summary.
- [x] `[T3.3]` `[ ]` `[M2-US3]` Ensure `python -m pytest tests/forensics/test_generate_fp_report.py -v` passes.

## 4. Milestone 3: Deep Investigation Visualization (M3-US2)

**User Story**: GraphViz Wallet Association Visualization

- [x] `[T4.1]` `[P]` `[M3-US2]` Implement `test_create_wallet_graph` in `tests/forensics/test_fund_flow_graph.py` validating `.dot` file generation.
- [x] `[T4.2]` `[ ]` `[M3-US2]` Implement `create_wallet_graph(edges, output_prefix)` in `forensics/fund_flow_graph.py` using `graphviz.Digraph`.
- [x] `[T4.3]` `[ ]` `[M3-US2]` Add graceful degradation for `graphviz.backend.execute.ExecutableNotFound` if system binary is missing.
- [x] `[T4.4]` `[ ]` `[M3-US2]` Ensure `python -m pytest tests/forensics/test_fund_flow_graph.py -v` passes.

## 5. Milestone 3: Report Consolidation (M3-US3)

**User Story**: Final Case Study Report Generation

- [x] `[T5.1]` `[ ]` `[M3-US3]` Generate 1-3 visual `.png` (or `.dot`) fund flow diagrams using `fund_flow_graph.py` with real data only (mapped to selected case alerts).
- [x] `[T5.2]` `[ ]` `[M3-US3]` Run `generate_report` to generate `forensics/v0.1_false_positive_report.md` based on manual labels.
- [x] `[T5.3]` `[ ]` `[M3-US3]` Draft final `case_study_00X.md` integrating the Graphviz plots, anomaly alerts, and external news timeline context.

## 6. Milestone 3: Individual Evidence Pack Submission (M3-US4)

**User Story**: Final Individual Submission Package

- [x] `[T6.1]` `[ ]` `[M3-US4]` Create/fill `forensics/Individual-Evidence-Pack-Milestone3.md` as a **submission index only**, consolidating links to Milestone 2 (`alerts_to_verify.csv`, `v0.1_false_positive_report.md`) and Milestone 3 (`case_study_00X.md`, fund-flow diagrams) outputs.
- [x] `[T6.2]` `[ ]` `[M3-US4]` In `forensics/Individual-Evidence-Pack-Milestone3.md`, add per-artifact status and location mapping (file path, purpose, completion state) **without re-writing case analysis/evidence content**.
- [x] `[T6.3]` `[ ]` `[M3-US4]` Add final submission checklist to `forensics/Individual-Evidence-Pack-Milestone3.md` and verify all referenced artifacts exist in `forensics/`.
- [x] `[T6.4]` `[ ]` `[M3-US4]` Perform final verification: `python -m pytest tests/forensics/test_export_alerts.py tests/forensics/test_generate_fp_report.py tests/forensics/test_fund_flow_graph.py -v` and include only the test-pass summary in the evidence pack.

