from pathlib import Path
from typing import List, Tuple
from .idempotency import compute_checksum
from datetime import datetime, timezone
import os
import json
from typing import Optional


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def discover_raw_files(raw_root: Path) -> List[Path]:
    raw_root = raw_root.resolve()
    files: List[Path] = []
    for p in raw_root.rglob("*.parquet"):
        files.append(p)
    return sorted(files)


def sanity_check_file(path: Path) -> None:
    if not path.exists():
        raise FileNotFoundError(path)
    if not path.is_file():
        raise IsADirectoryError(path)
    if path.is_symlink():
        raise RuntimeError("Symlinks are blocked in Sprint 1")
    size = path.stat().st_size
    if size == 0:
        raise RuntimeError("File is zero bytes")


def posix_relative(path: Path, raw_root: Path) -> str:
    # Ensure both paths are absolute/resolved so relative_to works across platforms
    return path.resolve().relative_to(raw_root.resolve()).as_posix()


def plan_run(files: List[Path], raw_root: Path) -> List[Tuple[Path, str, int, int]]:
    """Compute checksums and return list of tuples (path, checksum, bytes_hashed, duration_ms)
    Intended for dry-run planning and for ingestion.
    """
    results = []
    for p in files:
        sanity_check_file(p)
        checksum, bytes_hashed, duration_ms = compute_checksum(p)
        results.append((p, checksum, bytes_hashed, duration_ms))
    return results


def read_sidecar_source_uri(path: Path) -> Optional[str]:
    """If an adjacent sidecar `<file>.meta.json` exists, return its `source_uri`.
    Must not raise: any IO or parse error results in returning None.
    """
    try:
        sidecar = path.with_name(path.name + ".meta.json")
        if not sidecar.exists():
            return None
        # read and parse JSON
        with sidecar.open("r", encoding="utf-8") as fh:
            data = json.load(fh)
        return data.get("source_uri")
    except Exception:
        return None
