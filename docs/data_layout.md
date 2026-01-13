# Data Layout & Provenance

I write fetched data into a canonical, Hive‑style partitioned layout. Sidecars provide provenance linking files to their source.

## Canonical Layout
```text
raw_root/
  source=tlc/
    dataset=<dataset>/
      year=YYYY/
        month=MM/
          <dataset>_YYYY-MM.parquet
          <dataset>_YYYY-MM.parquet.meta.json
```

- `source=tlc` identifies the upstream (NYC TLC) transport source.
- `dataset=<dataset>` is the logical dataset name (e.g., `yellow_tripdata`).
- `year=YYYY` and `month=MM` partition storage to predictable locations.

## Sidecar (.meta.json)
Minimal schema:
```json
{
  "source_uri": "https://.../trip-data/yellow_tripdata_2024-01.parquet",
  "dataset": "yellow_tripdata",
  "year": 2024,
  "month": 1,
  "fetched_at_utc": "2026-01-13T12:00:00Z",
  "bytes": 12345678
}
```

## Mapping to SQLite
- `file_registry.raw_path` stores the POSIX‑relative path from `raw_root` to the file (e.g., `source=tlc/dataset=yellow_tripdata/year=2024/month=01/yellow_tripdata_2024-01.parquet`).
- `file_registry.source_uri` is populated best‑effort from the sidecar when present.
- `file_registry.checksum_sha256`, `file_size_bytes`, `bytes_hashed`, `checksum_duration_ms` are computed during ingestion.

## Path Normalization
- `raw_path` must be POSIX‑style regardless of OS: `Path(...).resolve().relative_to(raw_root).as_posix()`.

## Rationale
- Predictable directories let me reason easily, do bulk ops, and time‑partition storage.
- Sidecars decouple provenance from content so I don’t need to mutate binary payloads.

See also: ADRs [003](adr/003-canonical-raw-layout.md) and [005](adr/005-sidecar-provenance.md).
