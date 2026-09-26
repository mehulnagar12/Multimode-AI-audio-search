# AI Audio Search — Setup Guide

This guide prepares the environment for the two-speaker audio transcription,
chunking, PostgreSQL ingestion, retrieval, and evaluation pipeline.

Run the commands from the repository root. The repository uses
`data/callhome/` as the local directory for the downloaded source dataset.

## 1. Create a Python environment

Python 3.10 or newer is supported.

Windows PowerShell:

```powershell
py -3.10 -m venv .venv
.\.venv\Scripts\Activate.ps1
python --version
```

macOS/Linux:

```bash
python3.10 -m venv .venv
source .venv/bin/activate
python --version
```

## 2. Install dependencies

Windows PowerShell and macOS/Linux:

```text
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

On macOS/Linux, use `python3` instead of `python` if that is the active
interpreter name.

## 3. Obtain the dataset, if it is not already present

The source is the gated `talkbank/callhome` dataset. You need approved
Hugging Face access and an `HF_TOKEN`; do not commit the token.

Windows PowerShell:

```powershell
$env:HF_TOKEN = "YOUR_HUGGINGFACE_TOKEN"
python Tools/download_callhome_samples.py
```

macOS/Linux:

```bash
export HF_TOKEN="YOUR_HUGGINGFACE_TOKEN"
python3 Tools/download_callhome_samples.py
```

The utility downloads the first 10 samples into `data/callhome/audio/` and
`data/callhome/metadata/`. Do not rerun it over a dataset you need to preserve
without checking its overwrite behavior.

## 4. Prepare a local faster-whisper model

The transcription code expects a local CTranslate2 model and does not download
one implicitly.

Windows PowerShell:

```powershell
hf download Systran/faster-whisper-small `
  --local-dir models/faster-whisper-small
```

macOS/Linux:

```bash
hf download Systran/faster-whisper-small \
  --local-dir models/faster-whisper-small
```

If `hf` is not on `PATH`, use the executable inside `.venv` (`.venv/Scripts/hf.exe`
on Windows or `.venv/bin/hf` on macOS/Linux). The model directory should
contain files such as `config.json`, `model.bin`, and tokenizer files.

## 5. Prepare PostgreSQL and pgvector

Install PostgreSQL and the `vector` server extension for the PostgreSQL
version in use. The Python `pgvector` package alone is not sufficient.

```sql
SELECT name, default_version, installed_version
FROM pg_available_extensions
WHERE name = 'vector';

CREATE EXTENSION vector;
```

Run `CREATE EXTENSION` in the target database if the extension is available but
not yet installed. The project schema creates the `transcript_chunks` table
and its GIN full-text index.

## 6. Configure database credentials

Use credentials for the PostgreSQL instance that you can access. Do not commit
credentials.

Windows PowerShell:

```powershell
$env:DATABASE_URL = "postgresql://postgres:YOUR_PASSWORD@localhost:5432/YOUR_DATABASE"
```

macOS/Linux:

```bash
export DATABASE_URL="postgresql://postgres:YOUR_PASSWORD@localhost:5432/YOUR_DATABASE"
```

If the password contains URL-special characters, configure `PGHOST`,
`PGPORT`, `PGDATABASE`, `PGUSER`, and `PGPASSWORD` separately instead.

## 7. Verify the setup

Check the model path:

```text
models/faster-whisper-small/config.json
```

Check PostgreSQL connectivity with your platform's client, then run tests:

```text
python -m unittest discover -s tests -v
```

Use `python3` on macOS/Linux when required.

## 8. Run the pipeline

Transcribe all WAV files while skipping existing transcripts. This command
will process currently missing `call_006` and `call_009` files when their
transcripts do not exist:

```text
python -m transcription.pipeline --data-root data/callhome --model-path models/faster-whisper-small --device cpu --compute-type int8
```

Create chunks:

```text
python -m transcription.chunk_pipeline --data-root data/callhome
```

Ingest embeddings and metadata into PostgreSQL:

```text
python ingest_chunks.py --chunks-dir data/callhome/chunks --schema db/schema.sql
```

Search:

```text
python -m app.search "rolling kayak" --mode hybrid --top-k 5
```

Evaluate:

```text
python -m eval.evaluate --queries data/golden_queries.json --candidate-count 20 --report data/evaluation_report.json
```

On macOS/Linux, replace `python` with `python3` where needed. On Windows
PowerShell, the same commands can be entered as one line or split with the
PowerShell backtick continuation character.

## Output locations

- Transcripts: `data/callhome/transcripts/`
- Chunks: `data/callhome/chunks/`
- Golden queries: `data/golden_queries.json`
- Evaluation report: `data/evaluation_report.json`
- Database table: `transcript_chunks`
