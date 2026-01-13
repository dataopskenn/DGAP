from pathlib import Path
import hashlib
import time
from typing import Tuple

HASH_CHUNK_SIZE = 1024 * 1024  # 1MB

def compute_checksum(file_path: Path) -> Tuple[str, int, int]:
    """Compute SHA-256 checksum by streaming the file.

    Returns (hex_digest, bytes_hashed, duration_ms)
    """
    start = time.perf_counter()
    h = hashlib.sha256()
    bytes_hashed = 0

    with file_path.open("rb") as f:
        for chunk in iter(lambda: f.read(HASH_CHUNK_SIZE), b""):
            h.update(chunk)
            bytes_hashed += len(chunk)

    duration_ms = int((time.perf_counter() - start) * 1000)
    return h.hexdigest(), bytes_hashed, duration_ms
