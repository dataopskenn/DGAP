
# Decision Log — Sprint 1 (with Sprint 2 references)

Purpose and scope
-----------------
This decision log explains the engineering choices made when implementing Sprint 1. For each
decision we list the motivation, the alternatives considered, the risks accepted, and what is
deferred to later sprints.

1) Use SHA-256 (streaming) as the identity invariant
----------------------------------------------------
Decision: Every file's canonical identity is its streaming SHA-256 checksum computed while
reading the file in 1MB chunks.

Why: SHA-256 is a widely understood cryptographic hash with negligible collision probability
for our use case. A streaming implementation avoids loading entire files into memory, making
the approach scalable to large files.

Alternatives considered:
- File-system metadata (inode, mtime) — rejected because metadata can change independently
  of content and lacks cross-platform determinism.
- Content-based heuristics (size + partial hash) — rejected because partial checks can
  produce false negatives and weaken guarantees.

Risks accepted:
- Small risk of cryptographic collision (practically negligible for SHA-256).

Deferred:
- Future sprints may include additional integrity checks such as signatures or cross-store
  validation if external sources are involved.

2) Use SQLite as a metadata ledger with WAL and synchronous=NORMAL
------------------------------------------------------------------
Decision: Use a local SQLite database as an append-only ledger for `ingestion_runs` and
`file_registry`. When initializing, set PRAGMA journal_mode=WAL and synchronous=NORMAL and
enable foreign keys.

Why: SQLite is transactional, file-backed, and available in the Python standard library. WAL
mode offers good write concurrency and durability characteristics for local use. Using
SQLite avoids external service dependencies while making auditing and querying straightforward.

Alternatives considered:
- Plain files (CSV/JSON) — rejected due to atomicity and concurrency limitations.
- External DB (Postgres, etc.) — rejected due to added operational complexity for Sprint 1.

Risks accepted:
- Single-node storage: SQLite is not intended as a distributed ledger. For Sprint 1 this is
  acceptable because the scope is local ingestion provenance.

Deferred:
- Migration tooling and multi-node deployments (if needed) in future sprints.

3) POSIX-style `raw_path` and blocking symlinks
-----------------------------------------------
Decision: Store `raw_path` as a POSIX-style relative path (forward slashes) relative to the
configured raw root. The system explicitly rejects symlinks during sanity checks.

Why: POSIX normalization ensures consistent identity keys across platforms (Windows paths
may use backslashes but are normalized to forward slashes). Blocking symlinks avoids
security issues where a symlink could point to an unexpected or sensitive location.

Alternatives considered:
- Allow symlinks with canonical resolution — rejected to reduce attack surface for Sprint 1.

Risks accepted:
- Some workflows that rely on symlinks will need adjustment; this is acceptable for the
  conservative, auditable posture of Sprint 1.

4) Standard library only
------------------------
Decision: Implement Sprint 1 using Python standard library only (no third-party packages).

Why: Eliminates third-party supply-chain issues and simplifies the runtime environment for a
minimal, auditable prototype.

Alternatives considered:
- Use `pandas`/`pyarrow` for file discovery and schema inspection — rejected because that
  expands scope into data processing, which is explicitly out-of-scope for Sprint 1.

Deferred:
- Add-on tooling for testing, CI, and developer ergonomics can be considered in later sprints.

5) Checksum chunk size (1MB)
----------------------------
Decision: Use a 1MB read buffer for streaming checksums.

Why: 1MB is a practical tradeoff between system call overhead and memory usage. It works
reasonably well across file sizes common in raw data ingestion.

Alternatives considered:
- Larger chunk sizes — reduce syscalls but use more memory; could be considered if profiling
  indicates benefit.

Conclusion
----------
These decisions prioritise determinism, auditability, and minimal operational complexity. Each
choice is conservative by design: we preferred simple, explainable implementations that
produce verifiable evidence (checksums, run records) over feature breadth.


Sprint 2 references (fetch → ingest)
------------------------------------
Sprint 2 adds a transport layer that downloads files prior to ingestion. The following ADRs
capture the decisions and rationale:

- ADR-002: Fetch–Ingest Separation — fetch is transport-only; ingestion remains hashing + ledger.
- ADR-003: Canonical Raw Layout — deterministic `source=.../dataset=.../year=.../month=.../` paths.
- ADR-004: Staging and Atomic Commit — `_incoming/` with `.partial` and atomic rename to prevent partial files.
- ADR-005: Sidecar Provenance — `.meta.json` files provide `source_uri` without coupling fetch to SQLite.

How raw files arrive on disk (Sprint 2)
---------------------------------------
`dgap fetch` downloads into a staging directory under `raw_root`, then atomically moves files
into their final canonical paths. A `.meta.json` sidecar is written alongside each parquet file
containing the original `source_uri`. Ingestion reads this sidecar on a best-effort basis and
records `source_uri` in the ledger; sidecar absence or malformation does not change idempotency
or failure semantics.

