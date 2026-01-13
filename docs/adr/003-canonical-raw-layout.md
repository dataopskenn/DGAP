# ADR-003: Canonical Raw Layout (Hive-Style Partitioning)

**Status:** Accepted  
**Date:** 2026-01-13  
**Deciders:** DGAP Team

## Context

Fetched raw files need a deterministic, human-readable storage layout that:

- Allows the same file to be fetched multiple times without duplication.
- Makes the path computable *before* the download begins.
- Avoids polluting filenames with UUIDs or timestamps.
- Supports future tools that rely on partition discovery (e.g., query engines).

## Decision

All raw files land under `raw_root` using Hive-style key=value directories:

```
raw_root/
  source=tlc/
    dataset=<dataset_name>/
      year=YYYY/
        month=MM/
          <original_filename>.parquet
```

Example:

```
data/raw/source=tlc/dataset=yellow_tripdata/year=2024/month=01/yellow_tripdata_2024-01.parquet
```

Rules:

- Filenames remain stable (match the original remote filename).
- Paths are deterministic (same dataset/year/month always produces the same path).
- No UUIDs or timestamps in filenames.

## Consequences

**Good:**

- Paths are human-readable and self-documenting.
- Determinism enables idempotent fetch: if the file exists, skip.
- Future query engines can read partitions directly.

**Bad:**

- Deeper directory tree (more mkdir calls).
- Not suitable for datasets without year/month semantics (out of scope for Sprint 2).

**Neutral:**

- Layout is locked for Sprint 2; changes require a new ADR.
