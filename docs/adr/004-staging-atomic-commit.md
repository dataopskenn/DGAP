# ADR-004: Staging Directory and Atomic Commit

**Status:** Accepted  
**Date:** 2026-01-13  
**Deciders:** DGAP Team

## Context

Downloads can fail mid-stream due to network issues, process termination, or disk
errors. If a partially written file appears in the final location, downstream
consumers (including ingestion) could process corrupt data.

We need a strategy that guarantees:

1. Final locations contain only complete files.
2. Partial or failed downloads are isolated for forensic review.
3. Concurrent fetch processes cannot overwrite each other's work.

## Decision

Fetch uses a two-phase commit with a staging directory:

### Phase 1: Download into staging with `.partial` suffix

```
raw_root/_incoming/source=tlc/dataset=yellow_tripdata/year=2024/month=01/yellow_tripdata_2024-01.parquet.partial
```

The `.partial` suffix signals "download in progress."

### Phase 2: Atomic move to final destination

1. Rename `.partial` → staging filename (remove suffix).
2. Check if final destination exists:
   - If exists: delete staging file, log `status=skipped`, continue.
   - If not exists: atomically rename staging file → final destination.

Atomic rename is guaranteed by the OS when source and destination are on the same
filesystem. `_incoming/` is placed under `raw_root` to satisfy this requirement.

### Failure handling

| Scenario                       | Behavior                                              |
|--------------------------------|-------------------------------------------------------|
| Download fails mid-stream      | `.partial` remains in `_incoming/`; log error         |
| Atomic rename fails            | Leave staging file; log error; exit non-zero          |
| Final file already exists      | Delete staging file; log `status=skipped`             |
| Two processes fetch same file  | Second process skips (existence check)                |

### Cleanup policy

- Successful move: staging file is gone (moved, not copied).
- Failed move: staging file left for forensics.
- Orphaned files: warn about `.partial` files older than 24 hours on next run.
- Never auto-delete staging files.

## Consequences

**Good:**

- Final locations never contain partial files.
- Failures are isolated and recoverable.
- Idempotent: re-running fetch with same args is safe.

**Bad:**

- Requires staging directory on same filesystem as final destination.
- Orphaned files accumulate until manually cleaned.

**Neutral:**

- Explicit cleanup command may be added in a future sprint.
