import argparse
from pathlib import Path
from .ingest_raw import discover_raw_files, plan_run, posix_relative, sanity_check_file, utc_now, read_sidecar_source_uri
from .metadata import init_db, insert_run_start, update_run_end, insert_file_registry, get_registry_entry
from .idempotency import compute_checksum
import uuid
import traceback
import sys


def generate_run_id() -> str:
    from datetime import datetime, timezone

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    suffix = uuid.uuid4().hex[:8]
    return f"{timestamp}_{suffix}"


def format_run_summary(run_record: dict) -> str:
    duration = "?"
    if run_record.get("start_time") and run_record.get("end_time"):
        from datetime import datetime

        start = datetime.fromisoformat(run_record["start_time"])  # type: ignore
        end = datetime.fromisoformat(run_record["end_time"])  # type: ignore
        duration = f"{(end - start).total_seconds():.1f}s"

    return (
        f"{run_record['run_id']} | "
        f"{run_record['status']} | "
        f"{run_record['files_detected']} detected, "
        f"{run_record['files_ingested']} ingested, "
        f"{run_record['files_skipped']} skipped | "
        f"{duration}"
    )


def ingest_mode(dry_run: bool, raw_root: Path, db_path: Path) -> int:
    """Sprint 1 ingestion logic (unchanged behavior)."""
    run_id = generate_run_id()
    start_time = utc_now()

    # Discover files
    files = discover_raw_files(raw_root)
    files_detected = len(files)

    if dry_run:
        print(f"[DRY RUN] run_id: {run_id}")
        print(f"[DRY RUN] Files detected: {files_detected}")
        plan = plan_run(files, raw_root)
        for p, checksum, bytes_hashed, duration_ms in plan:
            raw_path = posix_relative(p, raw_root)
            print(f"  ✅ WOULD INGEST: {raw_path}")
        return 0

    # Normal run: initialize DB and insert run start
    conn = init_db(db_path)
    insert_run_start(conn, run_id, start_time)

    files_ingested = 0
    files_skipped = 0

    try:
        # compute and process
        for p in files:
            sanity_check_file(p)
            checksum, bytes_hashed, duration_ms = compute_checksum(p)
            file_size = p.stat().st_size
            raw_path = posix_relative(p, raw_root)

            existing = get_registry_entry(conn, raw_path)
            if existing:
                # existing is (raw_path, checksum_sha256)
                if existing[1] == checksum:
                    files_skipped += 1
                    print(f"SKIPPED: {raw_path}")
                    continue
                else:
                    # collision: same raw_path, different checksum -> fail hard
                    raise RuntimeError(f"Checksum collision for {raw_path}: existing={existing[1]} new={checksum}")

            # Read optional sidecar for source_uri (best-effort, never fails)
            source_uri = read_sidecar_source_uri(p)

            # insert new registry row
            insert_file_registry(
                conn,
                raw_path,
                p.name,
                checksum,
                file_size,
                bytes_hashed,
                duration_ms,
                source_uri,
                utc_now(),
                run_id,
            )
            files_ingested += 1

        end_time = utc_now()
        update_run_end(conn, run_id, end_time, "success", files_detected, files_ingested, files_skipped)

        # Fetch run record for summary
        cur = conn.execute("SELECT run_id, start_time, end_time, status, files_detected, files_ingested, files_skipped FROM ingestion_runs WHERE run_id = ?", (run_id,))
        row = cur.fetchone()
        if row:
            run_record = {
                "run_id": row[0],
                "start_time": row[1],
                "end_time": row[2],
                "status": row[3],
                "files_detected": row[4],
                "files_ingested": row[5],
                "files_skipped": row[6],
            }
            print(format_run_summary(run_record))

        return 0

    except Exception as e:
        tb = traceback.format_exc()
        end_time = utc_now()
        try:
            update_run_end(conn, run_id, end_time, "failure", files_detected, files_ingested, files_skipped, str(e), tb)
        except Exception:
            pass
        print("Run failed:", e, file=sys.stderr)
        print(tb, file=sys.stderr)
        return 2


def fetch_mode(args) -> int:
    """Sprint 2 fetch logic: download files into canonical layout."""
    from . import fetch_raw

    raw_root = Path(args.raw_root)
    dataset = args.dataset

    if args.year:
        start_year = int(args.year)
        if args.month:
            # Single month: --year YYYY --month M
            start_month = args.month
            end_year = start_year
            end_month = args.month
        else:
            # Full year: --year YYYY
            start_month = 1
            end_year = start_year
            end_month = 12
    else:
        # Range: --from YYYY-MM --to YYYY-MM
        def parse_ym(s: str):
            y, m = s.split("-")
            return int(y), int(m)

        start_year, start_month = parse_ym(args.from_month)
        end_year, end_month = parse_ym(args.to_month)

    return fetch_raw.fetch_range(raw_root, dataset, start_year, start_month, end_year, end_month)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="DGAP CLI — fetch and ingest raw files")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # fetch subcommand
    fetch_parser = subparsers.add_parser("fetch", help="Download raw files from remote sources")
    fetch_parser.add_argument("--dataset", required=True, help="Dataset name (e.g. yellow_tripdata)")
    fetch_parser.add_argument("--year", help="Fetch all 12 months for YYYY")
    fetch_parser.add_argument("--month", type=int, help="Single month (1-12), use with --year")
    fetch_parser.add_argument("--from", dest="from_month", help="Start month YYYY-MM (inclusive)")
    fetch_parser.add_argument("--to", dest="to_month", help="End month YYYY-MM (inclusive)")
    fetch_parser.add_argument("--raw-root", required=True, help="Raw root folder path")

    # ingest subcommand
    ingest_parser = subparsers.add_parser("ingest", help="Ingest raw files into ledger (Sprint 1)")
    ingest_parser.add_argument("--dry-run", action="store_true", help="Do not write DB; show plan")
    ingest_parser.add_argument("--raw-root", default="data/raw", help="Raw root folder (default: data/raw)")
    ingest_parser.add_argument("--db-path", default="data/ledger.db", help="SQLite DB path (default: data/ledger.db)")

    args = parser.parse_args()

    if args.command == "fetch":
        if not args.year and not (args.from_month and args.to_month):
            parser.error("fetch requires --year [--month M] or both --from and --to")
        if args.month and not args.year:
            parser.error("--month requires --year")
        rc = fetch_mode(args)
    elif args.command == "ingest":
        rc = ingest_mode(dry_run=args.dry_run, raw_root=Path(args.raw_root), db_path=Path(args.db_path))
    else:
        parser.print_help()
        rc = 1

    sys.exit(rc)
