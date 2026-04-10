# PolyWatch Validation History

This file records key validation artifacts and findings retained from earlier project phases in a neutral repository structure.

## Retained Evidence Assets

- Architecture draft image (legacy PNG): `docs/evidence/assets/system-architecture-draft.png`
- Architecture diagram (recommended SVG): `docs/evidence/assets/system-architecture.svg`
- Evidence package snapshot (2026-03-03): `docs/evidence/assets/evidence-pack-2026-03-03.pdf`
- Evidence package snapshot (2026-03-29): `docs/evidence/assets/evidence-pack-2026-03-29.pdf`

## Consolidated Validation Findings

- Controlled spike-injection checks verified anomaly sensitivity for Z-score detection.
- Threshold-based whale detection remained stable on fixed synthetic fixtures.
- Benford detection requirements were formalized and mapped to implemented event outputs.
- Backtest workflow was used to compare detector outputs with event-window labels on historical election data.

## Cross-Reference

- Architecture and threats: `docs/architecture-threat-model.md`
- Specifications: `docs/specs/wash_trading.feature`, `docs/specs/benford_law.feature`
- Automated tests: `tests/core_analysis/`, `tests/data_pipeline/`, `tests/forensics/`
