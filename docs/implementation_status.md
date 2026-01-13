# Implementation Status — DGAP Sprint 1 Prototype

Summary
- This repo contains a focused Sprint 1 prototype for DGAP: decision-grade raw ingestion + metadata ledger.
- Work completed (prototype preserved): code, CLI, SQLite ledger, docs scaffolding, and a helper script to push to GitHub.

# Implementation Status — DGAP Sprint 1 Prototype

Preface
-------
This document presents a detailed report of what has been implemented for Sprint 1 of
DGAP (Decision-Grade Acquisition Pipeline). The goal is to provide future engineers,
reviewers, and auditors a clear, textbook-level explanation of the system components,
how they interact, the invariants they preserve, and what is left to do.

Executive summary
-----------------
The prototype implements a local-file ingestion pipeline that:

- Discovers raw files under a configured `raw_root`.
- Applies structural sanity checks (existence, regular file, not a symlink, non-zero size).
- Computes a streaming SHA-256 checksum for each candidate file (1MB chunk buffer),
  while measuring `bytes_hashed` and `checksum_duration_ms`.
- Persists provenance and run metadata to a local SQLite ledger (`ingestion_runs` and
  `file_registry`) using a careful transactional strategy and PRAGMA settings.

This prototype intentionally avoids data inspection or transformation — its sole purpose
is to establish a reproducible, auditable record of file ingestion attempts.

Module-level overview
---------------------
dgap.main (Orchestration)
- Responsibilities: orchestrates discovery, hashing, and ledger operations. It implements
  two primary modes: a read-only `--dry-run` which computes hashes and prints a plan,
  and a normal run that writes to the SQLite ledger. `main` also handles top-level error
  capture and ensures runs are recorded in the ledger even on failure.

dgap.ingest_raw (Discovery and Guardrails)
- Responsibilities: recursively discover candidate files (currently `*.parquet`), enforce
  guardrails (no symlinks, non-zero size, regular file), and provide a POSIX-normalized
  `raw_path` computed via `Path.relative_to(raw_root).as_posix()` to guarantee consistent
  keys across platforms.

dgap.idempotency (Checksum Computation)
- Responsibilities: perform streaming SHA-256 hashing with a 1MB buffer, count bytes
  hashed, and measure elapsed time. This component returns `(hex_digest, bytes_hashed, duration_ms)`.

dgap.metadata (SQLite Ledger)
- Responsibilities: initialize the SQLite database with the required PRAGMA settings,
  create the `ingestion_runs` and `file_registry` tables, and expose helper functions to
  insert and update run-level and file-level records. The schema enforces `bytes_hashed == file_size_bytes`.

Data flow and invariants
------------------------
1. `main` generates a `run_id` using a UTC timestamp and a short random suffix.
2. Discovery returns a deterministic, sorted list of files under `raw_root`.
3. For each file:
   - Run guardrails to verify the file is safe and expected.
   - Compute the checksum and measurement metrics.
   - Query `file_registry` for existing `raw_path`:
       * If entry exists and checksum matches → mark as skipped (idempotent behavior).
       * If entry exists and checksum differs → treat as a collision and fail hard.
       * If no entry exists → insert a new `file_registry` row with `source_uri='local'`.
4. On success, update the `ingestion_runs` row with counts and `status='success'`.
   On exception, capture the traceback, update `status='failure'`, and surface the error.

Schema and PRAGMA choices
-------------------------
- `PRAGMA journal_mode=WAL;` and `PRAGMA synchronous=NORMAL;`: these provide durable
  writes and reasonable performance for local workloads while ensuring the ledger is
  consistently written.
- `ingestion_runs`: records run lifecycle and counts. Inserted at start (committed) so a
  run record always exists for post-mortem analysis.
- `file_registry`: stores `raw_path` (PK), `checksum_sha256`, `file_size_bytes`, `bytes_hashed`,
  and `checksum_duration_ms`. The `CHECK` constraint `bytes_hashed = file_size_bytes` ensures
  hash completeness.

Testing and validation performed
--------------------------------
- Dry-run smoke checks: validated that `--dry-run` computes hashes and prints a plan
  without creating or modifying the DB.
- Local ingestion workflow: validated that files are recorded in `file_registry` and
  that re-running the pipeline results in skipped files rather than duplicate records.
- Collision semantics: verified that a different checksum for an existing `raw_path`
  triggers a hard failure which is recorded in `ingestion_runs`.

Limitations and known constraints
---------------------------------
- No concurrency is implemented: files are processed sequentially to keep the prototype
  behavior simple and auditable.
- No schema or content validation: this sprint intentionally avoids parquet inspection
  and focuses solely on ingestion metadata.
- Local-only operation: Sprint 1 does not download remote files or integrate cloud storage.

Recommended next steps (practical roadmap)
-----------------------------------------
1. Add unit tests for `compute_checksum`, path normalization, and DB helpers.
2. Add CI to run `python -m dgap.main --dry-run` for each PR and to lint the code.
3. Provide canonical test files under `data/raw/tlc/` so the acceptance tests in
   `docs/sprint_1_validation.md` can be executed and documented.

Appendix: primary file locations
--------------------------------
- `dgap/main.py` — orchestration and CLI
- `dgap/ingest_raw.py` — discovery + guardrails
- `dgap/idempotency.py` — streaming checksum
- `dgap/metadata.py` — SQLite ledger helpers
