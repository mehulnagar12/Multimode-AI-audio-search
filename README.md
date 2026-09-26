# CALLHOME Local Hybrid Search PoC

This project builds a local search pipeline over timestamped CALLHOME speech.
The current persisted chunk set contains 621 chunks from 8 conversations.

For first-time installation, see the [setup guide](setup.md).

## Tech stack

- Python 3.10+
- faster-whisper for local ASR
- CALLHOME ground-truth speaker intervals
- PostgreSQL with pgvector
- PostgreSQL full-text search with `tsvector` and GIN
- sentence-transformers with `all-MiniLM-L6-v2` embeddings
- Reciprocal Rank Fusion for hybrid retrieval
- Python `unittest` for deterministic tests

## Architecture

```text
CALLHOME WAV + metadata
        |
        v
Local faster-whisper ASR
        |
        v
CALLHOME ground-truth speaker alignment
        |
        v
Speaker-aware time-based chunks
        |
        +--> local sentence-transformers embeddings
        |          |
        |          v
        |      PostgreSQL + pgvector
        |
        +--> PostgreSQL tsvector + GIN index
                   |
                   v
          lexical / semantic retrieval
                   |
                   v
             RRF ranked results
                   |
                   v
              Recall@K evaluation
```

### Pipeline components

- Transcription: `transcription/transcribe.py` uses a locally available
  faster-whisper CTranslate2 model. Transcript JSON is persisted so search
  does not retranscribe audio.
- Speaker alignment: `transcription/alignment.py` assigns each ASR segment to
  the CALLHOME speaker interval with maximum temporal overlap.
- Chunking: `transcription/chunking.py` merges adjacent same-speaker segments
  up to 30 seconds when the gap is at most 1 second. It never crosses a
  speaker boundary and produces deterministic chunk IDs.
- PostgreSQL FTS: `db/schema.sql` stores a generated `tsvector` and creates a
  GIN index. Lexical retrieval uses `websearch_to_tsquery` and `ts_rank_cd`.
- pgvector: transcript embeddings are stored as cosine-search vectors of
  dimension 384. Exact cosine search remains available as the quality
  baseline; HNSW DDL is included as an optional commented index.
- Local embeddings: `sentence-transformers/all-MiniLM-L6-v2` is centralized in
  `transcription/embedding_config.py`. Documents are embedded during
  ingestion; search embeds only the query.
- RRF: `app/retrieval.py` combines independently ranked lexical and semantic
  candidate lists using `1 / (k + rank)`, with default `k=60`. Raw lexical and
  cosine scores are not added together.

CALLHOME already provides verified timestamped speaker intervals. That ground
truth is used directly instead of running a diarization model, avoiding
unnecessary model cost and avoiding a second source of speaker-label error.
For production audio without speaker labels, a diarization stage such as
pyannote.audio could produce speaker intervals before ASR alignment.

## Evaluation

The golden queries are in `data/golden_queries.json`. The evaluator in
`eval/evaluate.py` runs lexical, semantic, and hybrid retrieval independently
and reports macro-average Recall@1, Recall@3, Recall@5, and MRR overall and by
query type.

The measured report in `data/evaluation_report.json` contains 29 queries with
20 candidates per retriever:

| Method | Recall@1 | Recall@3 | Recall@5 | MRR |
|---|---:|---:|---:|---:|
| lexical | 0.0977 | 0.1351 | 0.1351 | 0.2069 |
| semantic | 0.2713 | 0.5655 | 0.6730 | 0.8632 |
| hybrid | 0.2713 | 0.5655 | 0.6730 | 0.8632 |

This is a small manually labeled dataset, so the numbers are directional rather
than a production-quality benchmark. Hybrid did not add measurable benefit in
this run. Possible additional metrics include nDCG, precision@K, hit rate, and
per-conversation coverage.

## Production metrics to collect

- Retrieval: Recall@K, MRR/nDCG, p50/p95/p99 query latency, throughput, and
  error rate.
- Ingestion: ingestion throughput, embedding latency, transcription latency,
  index-build time, and database/index size.
- Speech quality: WER for transcription and DER when diarization is used.
- Vector quality: ANN recall against exact search at matching K values.

## Scaling

Exact pgvector cosine search is the quality baseline and is appropriate for a
small corpus. HNSW can be enabled for larger collections to reduce latency at
the cost of index build time, memory, and potentially lower recall. ANN recall
should be measured against exact search before choosing production parameters.

## Commands

Run commands from `D:\Me\g2` with the Python environment activated.

### Transcribe all WAV files, skipping existing transcripts

```powershell
python -m transcription.pipeline `
  --data-root D:\Me\g2\data\callhome `
  --model-path D:\Me\g2\models\faster-whisper-small `
  --device cpu `
  --compute-type int8
```

Check generated transcripts in:

```text
D:\Me\g2\data\callhome\transcripts\
```

Use `--force` to retranscribe existing files.

### Create chunks

```powershell
python -m transcription.chunk_pipeline `
  --data-root D:\Me\g2\data\callhome
```

Check generated chunks in:

```text
D:\Me\g2\data\callhome\chunks\
```

### Ingest into PostgreSQL

```powershell
$env:DATABASE_URL = "postgresql://postgres:YOUR_PASSWORD@localhost:5432/YOUR_DATABASE"
python .\ingest_chunks.py `
  --chunks-dir D:\Me\g2\data\callhome\chunks `
  --schema D:\Me\g2\db\schema.sql
```

PostgreSQL output is stored in the configured database, in the
`transcript_chunks` table. Ingestion logs report row count, vector dimension,
speaker nulls, and invalid timestamps.

The PostgreSQL server must have pgvector installed and `CREATE EXTENSION
vector` available.

### Search

```powershell
python -m app.search "rolling kayak" --mode lexical --top-k 5
python -m app.search "learning to kayak" --mode semantic --top-k 5
python -m app.search "kayak safety" --mode hybrid --top-k 5
```

Search results are printed to the terminal. Persisted source chunks remain in:

```text
D:\Me\g2\data\callhome\chunks\
```

Use `--candidate-count` to control candidates per retriever, `--rrf-k` to
control RRF smoothing, and `--log-level DEBUG` for detailed diagnostics.

### Tests

```powershell
python -m unittest discover -s tests -v
```

Test files are located in:

```text
D:\Me\g2\tests\
```

### Evaluation

```powershell
python -m eval.evaluate `
  --queries D:\Me\g2\data\golden_queries.json `
  --candidate-count 20 `
  --report D:\Me\g2\data\evaluation_report.json
```

Check the generated evaluation report at:

```text
D:\Me\g2\data\evaluation_report.json
```

## Current limitations

- The current persisted dataset is smaller than the original 10-file target;
  only the chunk files present under `data/callhome/chunks` are evaluated.
- ASR errors can affect both lexical matching and semantic relevance.
- The golden set is small and manually labeled.
- Chunk boundaries can split a topic across adjacent chunks.
- CALLHOME speaker labels are trusted ground truth; production unlabeled audio
  would need diarization and would introduce DER-related errors.
- Search currently returns ranked chunks, not transcript-level aggregation or
  answer synthesis.
