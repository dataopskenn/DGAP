# Sprint 2 Overview — Fetch → Ingest

## Goals

Sprint 2 introduces a **transport layer** that downloads raw files from remote sources
into a local filesystem layout. The existing Sprint 1 ingestion pipeline then runs
unchanged.

Sprint 2 answers one question:

> "How do raw files arrive on disk in a reproducible, auditable way before ingestion?"

## Non-Goals (Explicitly Out of Scope)

Sprint 2 does NOT:

- Inspect data semantics or Parquet contents.
- Transform data or create Bronze/Silver layers.
- Optimize performance or introduce concurrency.
- Implement retry logic with exponential backoff.
- Add schema validation or data cleaning.

These are candidates for Sprint 3+.

## Data Flow

```
┌────────────────────────────────────────────────────────────────────┐
│                         FETCH (Transport)                          │
│                                                                    │
│  1. Build source URL from dataset/year/month                       │
│  2. Download into staging: _incoming/.../<file>.parquet.partial    │
│  3. Verify: exists, size > 0, regular file                         │
│  4. Rename .partial → staging file                                 │
│  5. Atomic move staging → final destination                        │
│  6. Write .meta.json sidecar with source_uri                       │
│  7. Emit structured JSON log                                       │
└────────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌────────────────────────────────────────────────────────────────────┐
│                       INGEST (Sprint 1)                            │
│                                                                    │
│  1. Discover .parquet files under raw_root                         │
│  2. Apply guardrails (no symlinks, non-zero size)                  │
│  3. Compute SHA-256 checksum (streaming)                           │
│  4. Check idempotency: skip if already registered with same hash   │
│  5. Detect collision: fail if same path, different hash            │
│  6. Read .meta.json sidecar for source_uri (best-effort)           │
│  7. Insert into file_registry ledger                               │
│  8. Update ingestion_runs with counts and status                   │
└────────────────────────────────────────────────────────────────────┘
```

## Invariants Preserved from Sprint 1

| Invariant                          | Status      |
|------------------------------------|-------------|
| Guardrails (no symlinks, size > 0) | Unchanged   |
| SHA-256 streaming checksum         | Unchanged   |
| Idempotency (skip if same hash)    | Unchanged   |
| Collision detection (fail if diff) | Unchanged   |
| Ledger schema                      | Unchanged   |
| `bytes_hashed == file_size_bytes`  | Unchanged   |

## New Artifacts

| Artifact                       | Purpose                                      |
|--------------------------------|----------------------------------------------|
| `dgap/fetch_raw.py`            | Transport: download, stage, atomic commit    |
| `.meta.json` sidecar files     | Provenance: source_uri, dataset, year, month |
| `_incoming/` staging directory | Isolation of partial/failed downloads        |

## CLI Commands

### Fetch (Sprint 2)

```bash
python -m dgap.main fetch --dataset yellow_tripdata --year 2024 --raw-root data/raw
python -m dgap.main fetch --dataset yellow_tripdata --from 2024-01 --to 2024-03 --raw-root data/raw
```

### Ingest (Sprint 1, unchanged)

```bash
python -m dgap.main ingest --raw-root data/raw --db-path data/ledger.db
```

## Logging

Fetch emits structured JSON logs (one line per file):

```json
{
  "timestamp": "2026-01-13T14:23:45.123Z",
  "level": "INFO",
  "action": "fetch",
  "dataset": "yellow_tripdata",
  "year": 2024,
  "month": 1,
  "source_uri": "https://d37ci6vzurychx.cloudfront.net/trip-data/yellow_tripdata_2024-01.parquet",
  "target_path": "data/raw/source=tlc/dataset=yellow_tripdata/year=2024/month=01/yellow_tripdata_2024-01.parquet",
  "bytes": 123456789,
  "duration_ms": 4523,
  "status": "downloaded",
  "reason": null
}
```

## Related ADRs

- [ADR-002: Fetch–Ingest Separation](adr/002-fetch-ingest-separation.md)
- [ADR-003: Canonical Raw Layout](adr/003-canonical-raw-layout.md)
- [ADR-004: Staging and Atomic Commit](adr/004-staging-atomic-commit.md)
- [ADR-005: Sidecar Provenance](adr/005-sidecar-provenance.md)
