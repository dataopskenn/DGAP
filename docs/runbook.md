# Runbook & Troubleshooting

Day‑to‑day operations, common tasks, and recovery procedures for DGAP.

## Common Operations

### First‑Time Setup
```powershell
# Create directory structure
mkdir -p data/raw

# Fetch sample data
python -m dgap.main fetch --dataset yellow_tripdata --year 2024 --month 1 --raw-root data/raw

# Initial ingestion
python -m dgap.main ingest --raw-root data/raw --db-path data/ledger.db
```

### Regular Operations
```powershell
# Fetch new month
python -m dgap.main fetch --dataset yellow_tripdata --year 2024 --month 2 --raw-root data/raw

# Ingest new files
python -m dgap.main ingest --raw-root data/raw --db-path data/ledger.db

# Dry‑run before real ingestion (safety check)
python -m dgap.main ingest --raw-root data/raw --db-path data/ledger.db --dry-run
```

### Verification
```powershell
# Check ledger via Python (Windows‑friendly)
python -c "
import sqlite3
con = sqlite3.connect('data/ledger.db')
rows = con.execute('SELECT COUNT(*) FROM file_registry').fetchone()
print(f'Files ingested: {rows[0]}')
con.close()
"

# List recent runs
python -c "
import sqlite3
con = sqlite3.connect('data/ledger.db')
for row in con.execute('SELECT run_id, status, files_seen, files_ingested FROM ingestion_runs ORDER BY started_at_utc DESC LIMIT 5'):
    print(f'{row[0]}: {row[1]} ({row[3]}/{row[2]} files)')
con.close()
"
```

## Exit Codes
- `0`: Success
- `1`: General error (collision, guardrail failure, file system issue)
- `2`: Invalid CLI arguments

## Status Values
### Fetch
- `success`: Downloaded and moved to final location
- `skipped`: File already exists at destination
- `error`: Network, filesystem, or validation failure

### Ingestion
- `success`: New file ingested to ledger
- `idempotent`: File skipped (same checksum)
- `collision`: Same `raw_path`, different checksum (run fails)
- `guardrail`: File skipped (not regular, zero size, etc.)

## Common Issues

### Fetch Failures
**Network timeout/404**
- Check source URL pattern and dataset name
- Verify year/month combination exists upstream

**Permission denied on move**
- Ensure `raw_root` directory is writable
- Check antivirus isn't locking `.parquet` files

**Disk space**
- Monitor staging directory `_incoming/` for partial downloads
- Clean failed `.partial` files manually if needed

### Ingestion Failures
**Collision detected**
- Same `raw_path` with different checksum indicates file corruption or overwrite
- Recovery: rename/backup conflicting file, re‑fetch clean copy
- Investigation: compare file sizes, timestamps, source URIs in sidecars

**Database locked**
- Another ingestion process may be running
- Check for stale `.db‑wal` files and remove if safe

**Permission denied on SQLite**
- Ensure database directory is writable
- Check file permissions on existing `.db` file

## Recovery Procedures

### Collision Recovery
```powershell
# 1. Identify the collision
python -m dgap.main ingest --raw-root data/raw --db-path data/ledger.db --dry-run

# 2. Backup the conflicting file
$conflicted = "data/raw/source=tlc/dataset=yellow_tripdata/year=2024/month=01/yellow_tripdata_2024-01.parquet"
Copy-Item $conflicted "$conflicted.backup"

# 3. Remove and re‑fetch
Remove-Item $conflicted, "$conflicted.meta.json" -Force
python -m dgap.main fetch --dataset yellow_tripdata --year 2024 --month 1 --raw-root data/raw

# 4. Re‑ingest
python -m dgap.main ingest --raw-root data/raw --db-path data/ledger.db
```

### Partial State Cleanup
```powershell
# Clean staging area
Remove-Item -Recurse -Force data/raw/_incoming/* -ErrorAction SilentlyContinue

# Remove orphaned .partial files
Get-ChildItem -Recurse data/raw -Filter "*.partial" | Remove-Item -Force
```

### Ledger Inspection
```powershell
# Find files without source_uri (pre‑fetch ingestion)
python -c "
import sqlite3
con = sqlite3.connect('data/ledger.db')
for row in con.execute('SELECT raw_path FROM file_registry WHERE source_uri IS NULL'):
    print(row[0])
con.close()
"

# Check for checksum mismatches
python -c "
import sqlite3
con = sqlite3.connect('data/ledger.db')
for row in con.execute('SELECT raw_path FROM file_registry WHERE bytes_hashed != file_size_bytes'):
    print(f'Mismatch: {row[0]}')
con.close()
"
```