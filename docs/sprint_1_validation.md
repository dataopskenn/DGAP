
**Sprint 1 Validation Plan and Results**
How raw files arrive on disk (Sprint 2)
--------------------------------------
- Use `python -m dgap.main fetch` to download raw files into `raw_root` before running
	ingestion. Fetch writes files into `source=tlc/dataset=.../year=YYYY/month=MM/` and
	creates a `.meta.json` sidecar with `source_uri`.
- Ingestion remains unchanged: it does not perform any HTTP requests and will never fail
	due to a missing or malformed sidecar. Sidecar presence does not affect idempotency or
	collision logic.


Purpose
-------
This document records the acceptance tests for Sprint 1. The tests demonstrate:

- A successful initial ingestion of three canonical raw files.
- Idempotent behavior on re-run (already-ingested files are skipped).
- Collision detection when a file with the same `raw_path` has a differing checksum.

Prerequisites
-------------
- Place the canonical test files under `data/raw/tlc/`:
	- `yellow_tripdata_2023-01.parquet`
	- `yellow_tripdata_2023-02.parquet`
	- `yellow_tripdata_2023-03.parquet`
- Ensure your Python environment is 3.9+ and you run from the repository root.

Commands to run
---------------
1. Dry-run (plan only):

	 python -m dgap.main ingest --dry-run

2. Normal ingestion (writes `data/ledger.db`):

	 python -m dgap.main ingest

3. Re-run to demonstrate idempotency:

	 python -m dgap.main ingest

4. Collision test (manual step): corrupt or replace one of the three files in place
	 (for example, append a few bytes to `yellow_tripdata_2023-02.parquet`) then:

	 python -m dgap.main ingest

What to capture in this document
--------------------------------
- Full CLI stdout for each of the four runs above.
- The results of the following SQL queries against the created `data/ledger.db` after runs:

	- List ingestion runs (ordered by start):

		SELECT run_id, status, detected_files, ingested_files, skipped_files, error_message
		FROM ingestion_runs ORDER BY start_time DESC;

	- List file registry contents:

		SELECT raw_path, checksum_sha256, file_size_bytes, bytes_hashed, checksum_duration_ms
		FROM file_registry ORDER BY raw_path;

Validation acceptance criteria
----------------------------
- First ingestion: `ingestion_runs` shows `status='success'` and `ingested_files = 3`.
- Second ingestion: `ingestion_runs` shows `status='success'` and `ingested_files = 0`, `skipped_files = 3`.
- Collision run: `ingestion_runs` shows `status='failure'` and the recent failure row contains a
	clear `error_message` describing a checksum collision for the affected `raw_path`.

Place the captured CLI outputs and query results below when ready.
