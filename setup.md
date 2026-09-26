# Setup Guide

This guide prepares the local environment for the CALLHOME transcription,
chunking, PostgreSQL ingestion, retrieval, and evaluation pipeline.

## 1. Open the project

Change into the repository directory. For example:

```powershell
cd path/to/repository
```

## 2. Create and activate a Python environment

Python 3.10 or newer is supported.

```powershell
py -3.10 -m venv .venv
.\.venv\Scripts\Activate.ps1
python --version
```

If PowerShell blocks activation, run PowerShell with an appropriate execution
policy or activate the environment using its `activate.bat` script.

## 3. Install Python dependencies

```powershell
python -m pip install --upgrade pip
pip install -r requirements.txt
```

The dependency installation provides:

- faster-whisper for local transcription;
- sentence-transformers for local embeddings;
- psycopg for PostgreSQL connections;
- pgvector Python support;
- Hugging Face datasets support for the existing download utility.

## 4. Prepare a local faster-whisper model

The transcription code expects a local CTranslate2 faster-whisper model
directory and does not download a model implicitly.

Example using the Hugging Face CLI:

```powershell
hf download Systran/faster-whisper-small `
  --local-dir models/faster-whisper-small
```

If `hf` is not on `PATH`, use the executable in the active environment:

```powershell
& ".\.venv\Scripts\hf.exe" download Systran/faster-whisper-small `
  --local-dir models/faster-whisper-small
```

The model directory should contain files such as `config.json`, `model.bin`,
and tokenizer files.

## 5. Prepare PostgreSQL and pgvector

Install PostgreSQL and ensure the `vector` server extension is installed for
the exact PostgreSQL version being used. The Python `pgvector` package alone is
not sufficient.

Verify availability in pgAdmin Query Tool:

```sql
SELECT name, default_version, installed_version
FROM pg_available_extensions
WHERE name = 'vector';
```

If the extension is available but not installed in the target database:

```sql
CREATE EXTENSION vector;
```

The schema also creates the `transcript_chunks` table and GIN full-text index.

## 6. Configure database credentials

Use the same host, port, user, password, and database that work in pgAdmin.
Do not commit credentials to the repository.

```powershell
$env:DATABASE_URL = "postgresql://postgres:YOUR_PASSWORD@localhost:5432/YOUR_DATABASE"
```

If the password contains URL-special characters, use separate variables:

```powershell
Remove-Item Env:DATABASE_URL -ErrorAction SilentlyContinue
$env:PGHOST = "localhost"
$env:PGPORT = "5432"
$env:PGDATABASE = "YOUR_DATABASE"
$env:PGUSER = "postgres"
$env:PGPASSWORD = "YOUR_PASSWORD"
```

## 7. Verify the setup

Check the ASR model path:

```powershell
Test-Path models/faster-whisper-small/config.json
```

Check PostgreSQL reachability:

```powershell
Test-NetConnection localhost -Port 5432
```

Run the unit tests:

```powershell
python -m unittest discover -s tests -v
```

## 8. Run the application pipeline

Transcribe all WAV files while skipping existing transcripts:

```powershell
python -m transcription.pipeline `
  --data-root data/callhome `
  --model-path models/faster-whisper-small `
  --device cpu `
  --compute-type int8
```

Create searchable chunks:

```powershell
python -m transcription.chunk_pipeline `
  --data-root data/callhome
```

Generate embeddings and ingest chunks into PostgreSQL:

```powershell
python .\ingest_chunks.py `
  --chunks-dir data/callhome/chunks `
  --schema db/schema.sql
```

Run a search:

```powershell
python -m app.search "rolling kayak" --mode hybrid --top-k 5
```

Run evaluation:

```powershell
python -m eval.evaluate `
  --queries data/golden_queries.json `
  --candidate-count 20 `
  --report data/evaluation_report.json
```

## Important output locations

- Transcripts: `data/callhome/transcripts/`
- Chunks: `data/callhome/chunks/`
- Golden queries: `data/golden_queries.json`
- Evaluation report: `data/evaluation_report.json`
- Database table: `transcript_chunks`
