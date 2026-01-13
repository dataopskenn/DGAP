# DGAP  Decision‑Grade Acquisition Pipeline

Overview
--------
DGAP is a trustworthy, idempotent, auditable acquisition system for raw data. The implementation is organized into incremental sprints:

- **Sprint 1:** Ingestion  file discovery, streaming SHA‑256 checksums, SQLite ledger.
- **Sprint 2:** Fetch  transport‑only layer that downloads files into a canonical layout before ingestion.

The system is implemented in Python 3.9+ using only the standard library.

---

Sprint 2  Fetch → Ingest
-------------------------
Sprint 2 introduces a **transport layer** (`dgap fetch`) that downloads raw files from remote sources (initially NYC TLC) into a canonical filesystem layout. The Sprint 1 ingestion pipeline operates unchanged.

### Why separate transport from ingestion?

| Layer  | Responsibility                                      |
|--------|-----------------------------------------------------|
| Fetch  | Transport only: download, stage, atomic move        |
| Ingest | Observation + hashing + ledger (Sprint 1, unchanged)|

This separation ensures:

- Each layer can be tested independently.
- Failures are attributable to a single layer.
- Sprint 1 behavior is preserved verbatim.

### Staging and atomic commit

Fetch uses a two-phase commit to prevent partial writes:

1. **Download into staging** with `.partial` suffix:
   `raw_root/_incoming/.../file.parquet.partial`
2. **Atomic move** to final destination only after download completes and passes
   guardrails (exists, size > 0, regular file).

Partial or failed downloads never appear in final locations.

### Canonical raw layout

Fetched files land in a Hive-style partitioned structure:

```
raw_root/
  source=tlc/
    dataset=yellow_tripdata/
      year=2024/
        month=01/
          yellow_tripdata_2024-01.parquet
          yellow_tripdata_2024-01.parquet.meta.json   ← sidecar with source_uri
```

### Sidecar provenance

Fetch writes a `.meta.json` sidecar for each parquet file containing the source URL,
dataset, year, month, fetch timestamp, and byte count. Ingestion reads this sidecar
(best-effort) and records `source_uri` in the ledger. Missing or malformed sidecars
do not fail ingestion.

### Quick start (Sprint 2)

Prerequisites: Python 3.9+, sqlite3 CLI (or use Python snippets below).

```powershell
# Step 1: Fetch raw files
python -m dgap.main fetch --dataset yellow_tripdata --year 2024 --raw-root data/raw

# Step 2: Ingest (Sprint 1, unchanged)
python -m dgap.main ingest --raw-root data/raw --db-path data/ledger.db

# Step 3: Verify (sqlite3 CLI)
sqlite3 data/ledger.db "SELECT raw_path, source_uri, checksum_sha256 FROM file_registry LIMIT 5;"

# Step 3: Verify (Python alternative)
python -c "import sqlite3; con=sqlite3.connect('data/ledger.db'); [print(r) for r in con.execute('SELECT raw_path, source_uri, checksum_sha256 FROM file_registry LIMIT 5')]; con.close()"
```

### Documentation

- [Docs Index](docs/README.md)
- [Sprint 2 Overview](docs/sprint_2_overview.md)
- [Fetch Guide](docs/fetch_guide.md)
- [Ingestion Guide](docs/ingestion_guide.md)
- [Architecture](docs/architecture.md)
- [Data Layout & Provenance](docs/data_layout.md)
- [ADR‑002: Fetch–Ingest Separation](docs/adr/002-fetch-ingest-separation.md)
- [ADR‑003: Canonical Raw Layout](docs/adr/003-canonical-raw-layout.md)
- [ADR‑004: Staging and Atomic Commit](docs/adr/004-staging-atomic-commit.md)
- [ADR‑005: Sidecar Provenance](docs/adr/005-sidecar-provenance.md)
- [Future Work](docs/future_work.md)

---

Sprint 1  Ingestion
--------------------
Sprint 1 implements the minimal, foundational capabilities required to establish provenance and immutability guarantees for ingested files.

### How raw files arrive on disk (Sprint 2)
- The fetch layer retrieves files into a canonical layout under `raw_root` using a staging directory (`_incoming/`) and atomic moves so partial files never appear in final locations.
- For each `.parquet` file, the system writes a `.meta.json` sidecar containing the `source_uri` and fetch metadata. Ingestion reads this sidecar (best‑effort) and records `source_uri` in the ledger. Missing or malformed sidecars never cause ingestion to fail and do not affect idempotency.
- Ingestion has no HTTP logic and no access to remote systems; it only observes local files and writes to SQLite.

### Goals and guarantees
- Immutability: raw files are never modified in place.
- Idempotency: re-running the ingestion does not produce duplicate registry entries.
- Auditable ledger: every run (success or failure) is recorded in SQLite with timestamps and
	error diagnostics.
- Deterministic identity: files are identified by a POSIX relative path plus a streaming
	SHA-256 checksum computed with a 1MB chunk size.

High‑level architecture
-----------------------
- `dgap.main`  Orchestrates runs and exposes a simple CLI (supports `--dry-run`).
- `dgap.ingest_raw`  Discovers files under a configured `raw` root, verifies guardrails (exists, regular file, not a symlink, non‑zero size), and converts paths to POSIX‑relative `raw_path` values.
- `dgap.idempotency`  Computes SHA‑256 checksums by streaming file bytes and measures computation time and bytes hashed.
- `dgap.metadata`  Initializes and manages the SQLite ledger (tables: `ingestion_runs`, `file_registry`) and enforces PRAGMA settings for durability and atomicity.

Getting started (examples)
--------------------------
Prerequisites: Python 3.9+ available on PATH.

Run a read‑only plan (dry‑run):

```powershell
python -m dgap.main ingest --dry-run
```

This discovers candidate files and computes checksums to determine which files would be ingested or skipped. Dry‑run performs hashing but does not write the SQLite ledger.

Run a normal ingestion (writes `data/ledger.db`):

```powershell
python -m dgap.main ingest
```

By default the system looks for files under `data/raw/` and creates `data/ledger.db`. Use `--raw-root` and `--db-path` CLI flags to change these locations.

Data model and important implementation details
----------------------------------------------
- `raw_path`: a POSIX-style relative path under the configured raw root. This is the canonical
	identity key for files in the registry (use `Path.relative_to(...).as_posix()` to compute it).
- `checksum_sha256`: computed via streaming read with a chunk size of 1MB (no file is fully
	loaded into memory). The implementation measures `bytes_hashed` and `checksum_duration_ms`.
- SQLite ledger: two main tables
	- `ingestion_runs` records run-level metadata (start/end times, status, counts, errors)
	- `file_registry` stores one row per unique `raw_path` with checksum and provenance

Design constraints and rationale
--------------------------------
The implementation intentionally restricts the problem surface to ensure reproducibility and auditability:
- Standard library only  no third‑party dependencies to reduce supply‑chain and environment variability.
- No schema inspection or parquet parsing  this sprint is about ingestion and provenance, not data validation or analytics.

Where to look in the source
---------------------------
- `dgap/main.py`  entrypoint and run orchestration.
- `dgap/ingest_raw.py`  discovery and guardrails.
- `dgap/idempotency.py`  checksum implementation.
- `dgap/metadata.py`  schema and DB interactions.

Validation and tests
--------------------
The system is validated with three acceptance tests (manual or scripted):
1. First run: ingest a locked set of files and create registry rows.
2. Second run: re‑run to verify idempotency (files are skipped, no duplicates).
3. Collision: simulate a file with the same `raw_path` but different checksum and verify the pipeline fails and records an error.

See [docs/sprint_1_validation.md](docs/sprint_1_validation.md) for a reproducible step‑by‑step validation guide and [docs/decision_log.md](docs/decision_log.md) for design rationale.

