# ADR-005: Sidecar Files for Provenance

**Status:** Accepted  
**Date:** 2026-01-13  
**Deciders:** DGAP Team

## Context

Ingestion (Sprint 1) records a `source_uri` in the SQLite ledger. Before Sprint 2,
files were assumed to be local, so `source_uri` was set to `'local'` or `NULL`.

With Sprint 2, files are downloaded from remote URLs. We need a mechanism to pass the
source URL from fetch to ingest without:

- Having fetch write to SQLite (violates layer separation).
- Coupling ingestion to HTTP logic.
- Failing ingestion if provenance metadata is missing.

## Decision

Fetch writes a sidecar JSON file alongside each downloaded `.parquet` file:

```
yellow_tripdata_2024-01.parquet
yellow_tripdata_2024-01.parquet.meta.json
```

### Sidecar schema (locked for Sprint 2)

```json
{
  "source_uri": "https://d37ci6vzurychx.cloudfront.net/trip-data/yellow_tripdata_2024-01.parquet",
  "dataset": "yellow_tripdata",
  "year": 2024,
  "month": 1,
  "fetched_at_utc": "2026-01-13T14:23:45Z",
  "bytes": 123456789
}
```

### Ingestion integration

When ingesting a `.parquet` file:

1. Check for adjacent `.meta.json`.
2. If present, read `source_uri` and record in `file_registry.source_uri`.
3. If absent or malformed, record `source_uri` as `NULL`.

### Rules

- Sidecar files are best-effort enrichment.
- Fetch must write sidecar files.
- Fetch must not write to SQLite.
- Ingestion must NEVER fail because a sidecar is missing or malformed.
- Sidecar presence must not affect idempotency or collision logic.

## Consequences

**Good:**

- Fetch and ingest remain decoupled.
- Provenance is auditable (sidecar files can be inspected independently).
- Backwards-compatible: files without sidecars still ingest successfully.

**Bad:**

- Extra file per parquet (doubles file count in raw directories).
- Sidecar and parquet can become out of sync if one is deleted.

**Neutral:**

- Sidecar schema may be extended in future sprints (additive only).
