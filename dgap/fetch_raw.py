import json
import os
import sys
import time
from pathlib import Path
from typing import Iterable, Tuple
from urllib.request import urlopen, Request
from urllib.error import HTTPError, URLError
from datetime import datetime, timezone


TLC_URL = "https://d37ci6vzurychx.cloudfront.net/trip-data/{dataset}_{year}-{month:02d}.parquet"


def utc_now() -> str:
    """Return current UTC time as ISO8601 string."""
    return datetime.now(timezone.utc).isoformat()


def _inc_month(year: int, month: int) -> tuple:
    """Increment year/month by one month."""
    if month == 12:
        return year + 1, 1
    return year, month + 1


def _make_targets(raw_root: Path, dataset: str, year: int, month: int) -> Tuple[Path, Path, Path]:
    """Return (final_path, staging_path, partial_path) for given dataset/year/month."""
    final = raw_root / f"source=tlc" / f"dataset={dataset}" / f"year={year:04d}" / f"month={month:02d}" / f"{dataset}_{year}-{month:02d}.parquet"
    staging_dir = raw_root / "_incoming" / "source=tlc" / f"dataset={dataset}" / f"year={year:04d}" / f"month={month:02d}"
    staging_dir.mkdir(parents=True, exist_ok=True)
    partial = staging_dir / f"{dataset}_{year}-{month:02d}.parquet.partial"
    staging = staging_dir / f"{dataset}_{year}-{month:02d}.parquet"
    return final, staging, partial


def _write_sidecar(final_path: Path, source_uri: str, dataset: str, year: int, month: int, bytes_count: int) -> None:
    sidecar = final_path.with_name(final_path.name + ".meta.json")
    payload = {
        "source_uri": source_uri,
        "dataset": dataset,
        "year": year,
        "month": month,
        "fetched_at_utc": utc_now(),
        "bytes": bytes_count,
    }
    with sidecar.open("w", encoding="utf-8") as fh:
        json.dump(payload, fh, ensure_ascii=False)


def _log(record: dict) -> None:
    # One-line JSON structured log
    print(json.dumps(record, default=str), flush=True)


def fetch_range(raw_root: Path, dataset: str, start_year: int, start_month: int, end_year: int, end_month: int) -> int:
    """Fetch inclusive range from start_year/start_month to end_year/end_month.
    Returns 0 on success (no failures), non-zero if any failed downloads (network/server).
    """
    cur_year = start_year
    cur_month = start_month
    failures = 0

    while (cur_year < end_year) or (cur_year == end_year and cur_month <= end_month):
        final, staging, partial = _make_targets(raw_root, dataset, cur_year, cur_month)
        source_uri = TLC_URL.format(dataset=dataset, year=cur_year, month=cur_month)
        start_ts = time.time()
        log_base = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": "INFO",
            "action": "fetch",
            "dataset": dataset,
            "year": cur_year,
            "month": cur_month,
            "source_uri": source_uri,
            "target_path": str(final.as_posix()),
            "raw_root": str(raw_root.as_posix()),
            "bytes": None,
            "duration_ms": None,
            "status": None,
            "reason": None,
        }

        try:
            # If final exists already, skip without downloading
            if final.exists():
                log = dict(log_base)
                log.update({"status": "skipped", "reason": "already_exists", "duration_ms": 0})
                _log(log)
                cur_year, cur_month = _inc_month(cur_year, cur_month)
                continue

            # Stream download into partial file
            req = Request(source_uri, headers={"User-Agent": "dgap-fetch/1.0"})
            with urlopen(req, timeout=30) as resp:
                # Handle HTTP errors via exceptions
                with partial.open("wb") as outfh:
                    total = 0
                    while True:
                        chunk = resp.read(64 * 1024)
                        if not chunk:
                            break
                        outfh.write(chunk)
                        total += len(chunk)

            # Post-download checks
            if not partial.exists():
                log = dict(log_base)
                log.update({"status": "error", "reason": "zero_bytes"})
                _log(log)
                failures += 1
                cur_year, cur_month = _inc_month(cur_year, cur_month)
                continue

            size = partial.stat().st_size
            if size == 0:
                log = dict(log_base)
                log.update({"status": "error", "reason": "zero_bytes", "bytes": 0})
                _log(log)
                failures += 1
                cur_year, cur_month = _inc_month(cur_year, cur_month)
                continue

            # Rename partial -> staging (remove .partial suffix)
            try:
                partial.replace(staging)
            except Exception as e:
                log = dict(log_base)
                log.update({"status": "error", "reason": "rename_failed", "error": str(e)})
                _log(log)
                # leave partial for forensics
                return 2

            # Final atomic move: if final exists -> delete staging and mark skipped
            try:
                if final.exists():
                    # someone else created it
                    staging.unlink(missing_ok=True)
                    log = dict(log_base)
                    log.update({"status": "skipped", "reason": "already_exists", "bytes": size})
                    _log(log)
                else:
                    # ensure parent exists
                    final.parent.mkdir(parents=True, exist_ok=True)
                    staging.replace(final)
                    # write sidecar
                    _write_sidecar(final, source_uri, dataset, cur_year, cur_month, size)
                    duration_ms = int((time.time() - start_ts) * 1000)
                    log = dict(log_base)
                    log.update({"status": "success", "bytes": size, "duration_ms": duration_ms})
                    _log(log)
            except Exception as e:
                log = dict(log_base)
                log.update({"status": "error", "reason": "rename_failed", "error": str(e)})
                _log(log)
                return 2

        except HTTPError as he:
            code = he.code
            reason = "expected_absence" if code in (404, 403, 410) else "server_error"
            log = dict(log_base)
            log.update({"status": "skipped" if reason == "expected_absence" else "error", "reason": reason, "http_status": code})
            _log(log)
            if reason != "expected_absence":
                failures += 1

        except URLError as ue:
            log = dict(log_base)
            log.update({"status": "error", "reason": "network_error", "error": str(ue)})
            _log(log)
            failures += 1

        except Exception as e:
            log = dict(log_base)
            log.update({"status": "error", "reason": "network_error", "error": str(e)})
            _log(log)
            failures += 1

        cur_year, cur_month = _inc_month(cur_year, cur_month)

    return 1 if failures > 0 else 0
