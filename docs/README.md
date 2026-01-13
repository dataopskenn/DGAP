# DGAP Documentation Index

This directory contains deep-dive documentation for the decision‑grade raw acquisition pipeline. Start with this index to explore the architecture, sprint guides, data layout, and operations.

## Quick Map
- Overview: read the repository [README](../README.md)
- Architecture: how I structured components and flows  [architecture.md](architecture.md)
- Sprint 2 (Fetch): transport‑only layer  [fetch_guide.md](fetch_guide.md)
- Sprint 1 (Ingestion): hashing + ledger design  [ingestion_guide.md](ingestion_guide.md)
- Data Layout & Provenance: canonical directories and sidecars  [data_layout.md](data_layout.md)
- Runbook & Troubleshooting  [runbook.md](runbook.md)
- Security & Privacy  [security_privacy.md](security_privacy.md)
- ADRs (decisions)  [adr/](adr/)

## Learning Path
1. Read [architecture.md](architecture.md) for the big picture.
2. Follow [fetch_guide.md](fetch_guide.md) to see the staging → atomic commit flow.
3. Study [ingestion_guide.md](ingestion_guide.md) for idempotent hashing and the SQLite ledger.
4. Use [data_layout.md](data_layout.md) when navigating raw storage and sidecars.
5. Keep [runbook.md](runbook.md) handy for day‑to‑day operations and recovery.
6. Review [security_privacy.md](security_privacy.md) before handling sensitive datasets.

## Related
- Sprint overview: [sprint_2_overview.md](sprint_2_overview.md) and [sprint_1_validation.md](sprint_1_validation.md)
- Decision log: [decision_log.md](decision_log.md)
- Future work: [future_work.md](future_work.md)
