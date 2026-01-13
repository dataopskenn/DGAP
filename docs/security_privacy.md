# Security & Privacy

How I protect data, secrets, and sensitive information in DGAP.

## Data Protection via .gitignore

My [.gitignore](.gitignore) prevents committing:

### Raw Data
- Entire `/data/` folder: no parquet files, staging, or downloaded content
- Binary formats: `*.parquet`, `*.zip`, `*.gz`, `*.tar`, etc.
- Sidecar files: `*.parquet.meta.json` (contain source URLs and metadata)

### Database State  
- SQLite files: `*.db`, `*.sqlite`, `*.sqlite3`
- WAL/journal: `*.db‑wal`, `*.db‑shm` (contain transaction state)

### Secrets & Credentials
- Environment files: `.env`, `.env.*`
- Keys/certificates: `*.pem`, `*.key`, `*.pfx`, `*.crt`, etc.
- Cloud credentials: `.aws/`, `.azure/`, `.gcp/`, `.git‑credentials`
- SSH: `.ssh/` directory contents

### Development Artifacts
- Python cache: `__pycache__/`, `*.pyc`, `.pytest_cache/`, `.mypy_cache/`
- Editor state: `.vscode/`, `.idea/`, `*.code‑workspace`
- Logs: `*.log`, `logs/`

## Privacy Considerations

### Dataset Content
- DGAP handles **transport and provenance only**; I don't parse parquet content
- Sensitive datasets (PII, financial, medical) remain opaque binaries during fetch/ingest
- Sidecar `.meta.json` files contain **source URLs only**, no dataset content

### Metadata Exposure
- `file_registry.source_uri`: upstream URL (may contain dataset/date hints)
- `file_registry.raw_path`: canonical path structure reveals dataset organization
- `ingestion_runs`: timestamps, run IDs, file counts (operational metadata)

### Redaction Strategy
For sensitive environments:
1. **Source URI masking**: modify sidecar write to store hashed/tokenized URIs
2. **Path obfuscation**: use content‑based directories instead of semantic names
3. **Audit controls**: restrict ledger access, enable SQL‑level logging

## Operational Security

### Network Access
- Fetch requires HTTPS access to `d37ci6vzurychx.cloudfront.net` (NYC TLC)
- No other network dependencies; ingestion is purely local
- Consider firewall rules for production fetch‑only hosts

### File System Permissions  
- `raw_root/`: readable by ingestion, writable by fetch
- `_incoming/`: staging area, should be cleaned regularly
- SQLite database: restrict access to DGAP operator account

### Transport Security
- All downloads via HTTPS (TLS 1.2+)
- Atomic moves prevent partial file exposure
- Checksums detect transport corruption

## Secrets Handling

### What DGAP Doesn't Store
- No API keys (public data source)
- No user credentials
- No database passwords (SQLite is file‑based)

### Local Security
- Run DGAP with minimal user privileges
- Store `data/` outside web‑accessible directories
- Backup ledger databases with encryption at rest

## Risk Assessment

### Low Risk
- Source URLs: public NYC TLC data, no authentication required
- Checksums: SHA‑256 hashes don't reveal content
- Timestamps: operational metadata for audit trails

### Medium Risk  
- Canonical paths: reveal dataset structure and time ranges
- Ledger queries: can infer data acquisition patterns
- Staging files: brief exposure during atomic moves

### High Risk (if applicable)
- Sensitive datasets: ensure proper data classification
- Multi‑tenant environments: isolate `raw_root` per tenant
- Compliance: verify retention policies align with data sources

## Compliance Notes

### Data Retention
- I don't automatically delete old files; implement retention policies externally
- Ledger grows monotonically; archive old `ingestion_runs` if needed
- Consider GDPR "right to be forgotten" if applicable to datasets

### Audit Capabilities  
- Complete provenance: `source_uri` + `checksum_sha256` + `ingested_at_utc`
- Immutable ledger: no UPDATE/DELETE operations on `file_registry`
- Run‑level tracking: all operations logged to `ingestion_runs`