# Future Work — Deferred from Sprint 2

This document lists capabilities explicitly deferred from Sprint 2. These are
candidates for Sprint 3 and beyond.

## Transport Enhancements

- **Retry logic with exponential backoff:** Currently, fetch makes a single attempt per
  file. Network transients could benefit from retries, but this adds complexity and
  state.
- **Parallel downloads:** Files are fetched sequentially. Parallelism could improve
  throughput but introduces concurrency concerns.
- **Configurable timeout:** Timeout is hardcoded. A CLI flag could allow tuning.
- **Resume partial downloads:** If a `.partial` file exists from a prior failed run,
  fetch could attempt to resume instead of restarting.

## Data Source Generalization

- **Additional sources:** Sprint 2 hardcodes NYC TLC URLs. Future sprints may add
  other public datasets or private sources.
- **Authentication:** Some sources require API keys or OAuth. Not implemented.
- **S3/GCS/Azure support:** Cloud storage backends are out of scope.

## Data Validation

- **Parquet schema inspection:** Verify column names and types match expectations.
- **Row count validation:** Ensure downloaded files are non-trivial.
- **Checksum verification at fetch time:** Compare against a known manifest (if
  available).

## Processing Layers

- **Bronze layer:** Raw files copied with minimal transformation.
- **Silver layer:** Cleaned, deduplicated, typed data.
- **DuckDB integration:** Use DuckDB for analytical queries over raw files.

## Operational

- **Automatic staging cleanup:** Command to purge orphaned `.partial` files older than
  N hours.
- **Metrics and monitoring:** Emit Prometheus-style metrics for fetch/ingest runs.
- **CI/CD integration:** GitHub Actions workflow for automated testing.

## Why These Are Deferred

Sprint 2's objective is narrow:

> "Get files onto disk in a reproducible, auditable way."

Each item above adds complexity, testing surface, or operational burden. By deferring
them, we keep Sprint 2 simple, auditable, and shippable.
