# PolyWatch Development Guidelines

Auto-generated for Member D (CHEN Sijie). Last updated: 2026-03-27

## Active Technologies
- Python 3.10+
- Pandas (Data Processing)
- Graphviz (Fund flow visualization)
- PostgreSQL (via `psycopg2`, reading from TimescaleDB)
- Pytest (Testing)

## Project Structure
```text
PolyWatch/
鈹溾攢鈹€ core_analysis/      # Member C algorithms & DB Interface
鈹?  鈹斺攢鈹€ db_interface.py # Shared DB read/write interface
鈹溾攢鈹€ forensics/          # Member D (Your current workspace)
鈹?  鈹溾攢鈹€ explain_presidential_2024_spikes.py
鈹?  鈹溾攢鈹€ manual_audit_log_001.md
鈹?  鈹斺攢鈹€ presidential_2024_spike_report.md
鈹溾攢鈹€ specs/              # Specification & Requirement files
鈹?  鈹溾攢鈹€ 001-milestone2-validation/
鈹?  鈹斺攢鈹€ 002-milestone3-investigation/
鈹溾攢鈹€ docs/plans/         # Implementation Plans
鈹?  鈹溾攢鈹€ 2026-03-27-milestone3-spec.md
鈹?  鈹斺攢鈹€ tasks.md        # <-- THE TASK LIST TO EXECUTE
鈹斺攢鈹€ tests/              # Pytest files
```

## Important Context
- You are implementing the tasks for **Milestone 2 (False Positive Report)** and **Milestone 3 (Fund Flow GraphViz)**.
- Read from DB using `core_analysis.db_interface.query_anomalies(slug, severity)`.
- Write reports and analysis to the `forensics/` folder.
- All testing should be driven via `pytest tests/ -v`.

## Active Feature Plan
We are executing the tasks defined in: `docs/plans/tasks.md`
Please read `docs/plans/tasks.md` thoroughly before beginning implementation.

<!-- MANUAL ADDITIONS START -->
<!-- MANUAL ADDITIONS END -->

