# ADR-002: Fetch–Ingest Separation

**Status:** Accepted  
**Date:** 2026-01-13  
**Deciders:** DGAP Team

## Context

Sprint 2 introduces downloading raw files from remote sources (initially NYC TLC).
We must decide how this new "fetch" capability relates to Sprint 1's ingestion logic.

Two approaches were considered:

1. **Unified pipeline:** Fetch downloads a file and immediately runs ingestion (hashing,
   ledger writes) in a single pass.
2. **Separated layers:** Fetch only transports files to disk; ingestion runs as a
   distinct, subsequent step.

Key constraints:

- Sprint 1 behavior (guardrails, hashing, idempotency, ledger writes) must remain
  unchanged.
- Audit requirements demand clear accountability: which step modified which artifact.
- Debugging partial failures is easier when each layer has one responsibility.

## Decision

We separate fetch and ingest into distinct layers with no overlap:

| Layer  | Responsibility                                     |
|--------|----------------------------------------------------|
| Fetch  | Transport only: download files, stage, atomic move |
| Ingest | Observation + hashing + ledger (Sprint 1)          |

Fetch must NOT:

- Compute checksums
- Write to SQLite
- Inspect Parquet contents

Ingest must NOT:

- Know about HTTP or remote URLs (it reads source_uri from a sidecar if present)

## Consequences

**Good:**

- Each layer can be tested independently.
- Failures are attributable to one layer.
- Sprint 1 behavior is preserved verbatim; no risk of regression.
- Easier to swap transport mechanisms in future sprints without touching ingestion.

**Bad:**

- Two CLI invocations required (`fetch` then `ingest`) instead of one.
- Slight increase in operational complexity for users.

**Neutral:**

- Sidecar files bridge provenance from fetch to ingest without coupling the layers.
