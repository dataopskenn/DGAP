import sqlite3
from pathlib import Path
from typing import Optional

SCHEMA = """
CREATE TABLE IF NOT EXISTS ingestion_runs (
    run_id TEXT PRIMARY KEY,
    start_time TEXT NOT NULL,
    end_time TEXT,
    status TEXT NOT NULL,
    files_detected INTEGER NOT NULL,
    files_ingested INTEGER NOT NULL,
    files_skipped INTEGER NOT NULL,
    error_message TEXT,
    error_traceback TEXT
);

CREATE TABLE IF NOT EXISTS file_registry (
    raw_path TEXT PRIMARY KEY,
    file_name TEXT NOT NULL,
    checksum_sha256 TEXT NOT NULL,
    file_size_bytes INTEGER NOT NULL,
    bytes_hashed INTEGER NOT NULL,
    checksum_duration_ms INTEGER,
    source_uri TEXT,
    first_seen_at TEXT NOT NULL,
    first_ingestion_run_id TEXT NOT NULL,
    CONSTRAINT bytes_match CHECK (bytes_hashed = file_size_bytes),
    FOREIGN KEY (first_ingestion_run_id) REFERENCES ingestion_runs(run_id)
);

CREATE INDEX IF NOT EXISTS idx_checksum ON file_registry(checksum_sha256);
CREATE INDEX IF NOT EXISTS idx_file_name ON file_registry(file_name);
"""


def init_db(db_path: Path) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path), timeout=30)
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA synchronous=NORMAL;")
    conn.execute("PRAGMA foreign_keys=ON;")
    cursor = conn.cursor()
    cursor.executescript(SCHEMA)
    conn.commit()
    return conn


def insert_run_start(conn: sqlite3.Connection, run_id: str, start_time: str) -> None:
    # Insert with default failure state; update on success later.
    conn.execute(
        "INSERT OR REPLACE INTO ingestion_runs (run_id, start_time, status, files_detected, files_ingested, files_skipped) VALUES (?, ?, ?, 0, 0, 0)",
        (run_id, start_time, "failure"),
    )
    conn.commit()


def update_run_end(
    conn: sqlite3.Connection,
    run_id: str,
    end_time: str,
    status: str,
    files_detected: int,
    files_ingested: int,
    files_skipped: int,
    error_message: Optional[str] = None,
    error_traceback: Optional[str] = None,
) -> None:
    conn.execute(
        "UPDATE ingestion_runs SET end_time = ?, status = ?, files_detected = ?, files_ingested = ?, files_skipped = ?, error_message = ?, error_traceback = ? WHERE run_id = ?",
        (end_time, status, files_detected, files_ingested, files_skipped, error_message, error_traceback, run_id),
    )
    conn.commit()


def insert_file_registry(
    conn: sqlite3.Connection,
    raw_path: str,
    file_name: str,
    checksum_sha256: str,
    file_size_bytes: int,
    bytes_hashed: int,
    checksum_duration_ms: int,
    source_uri: Optional[str],
    first_seen_at: str,
    first_ingestion_run_id: str,
) -> None:
    conn.execute(
        "INSERT INTO file_registry (raw_path, file_name, checksum_sha256, file_size_bytes, bytes_hashed, checksum_duration_ms, source_uri, first_seen_at, first_ingestion_run_id) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (raw_path, file_name, checksum_sha256, file_size_bytes, bytes_hashed, checksum_duration_ms, source_uri, first_seen_at, first_ingestion_run_id),
    )
    conn.commit()


def get_registry_entry(conn: sqlite3.Connection, raw_path: str):
    cur = conn.execute("SELECT raw_path, checksum_sha256 FROM file_registry WHERE raw_path = ?", (raw_path,))
    return cur.fetchone()
