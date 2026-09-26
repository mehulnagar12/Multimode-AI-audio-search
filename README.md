# AI Audio Search

This project builds a local search pipeline over timestamped conversation data.
The source dataset contains 10 conversations. The current persisted artifacts
contain 621 chunks from 8 conversations: `call_006` and `call_009` currently
have audio and metadata but no transcript or chunk output. Rerunning the
transcription command processes those missing files and changes the current
artifact counts and evaluation coverage.

For first-time installation, see the [setup guide](setup.md).

Project documentation: [submission](SUBMISSION.md) ·
[agent notes](AGENT_NOTES.md) · [task prompts and skills](prompt/)

## Tech stack

- Python 3.10+
- faster-whisper for local ASR
- Provided ground-truth speaker intervals
- PostgreSQL with pgvector
- PostgreSQL full-text search with `tsvector` and GIN
- sentence-transformers with `all-MiniLM-L6-v2` embeddings
- Reciprocal Rank Fusion for hybrid retrieval
- Python `unittest` for deterministic tests

## Architecture

```text
Two-speaker WAV + metadata
        |
        v
Local faster-whisper ASR
        |
        v
ground-truth speaker alignment
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
  the speaker interval with maximum temporal overlap.
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
- Dataset: the two-speaker conversations are used because they provide
  real conversational audio together with verified speaker intervals and
  timestamps, allowing speaker-aware alignment without adding diarization to
  this proof of concept. For production audio without speaker labels, a
  diarization stage such as `pyannote.audio` could produce speaker intervals
  before ASR alignment.

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
this run. The current schema uses PostgreSQL's `simple` text-search
configuration, which does not stem words or remove stop words. In addition,
`websearch_to_tsquery` requires the query terms to match the same chunk. As a
result, question-style queries can produce no lexical candidates; all 12
semantic queries in this report had zero lexical hits, so hybrid collapsed to
the semantic ranking. Possible additional metrics include nDCG, precision@K,
hit rate, and per-conversation coverage.

The semantic MRR of 0.8632 alongside Recall@1 of 0.2713 is not contradictory:
MRR measures the rank of the first relevant chunk, while Recall@1 divides the
number of relevant chunks retrieved at rank 1 by the total relevant chunks.
Twenty-eight of the 29 queries have multiple relevant chunks, so one relevant
result appearing early can produce high MRR while many other relevant chunks
remain below rank 1.

## Commands

Run commands from the repository root with the Python environment activated.

### Transcribe all WAV files, skipping existing transcripts

```powershell
python -m transcription.pipeline `
  --data-root data/callhome `
  --model-path models/faster-whisper-small `
  --device cpu `
  --compute-type int8
```

On macOS/Linux:

```bash
python3 -m transcription.pipeline \
  --data-root data/callhome \
  --model-path models/faster-whisper-small \
  --device cpu \
  --compute-type int8
```

Check generated transcripts in:

```text
data/callhome/transcripts/
```

Use `--force` to retranscribe existing files.

### Create chunks

```powershell
python -m transcription.chunk_pipeline `
  --data-root data/callhome
```

On macOS/Linux:

```bash
python3 -m transcription.chunk_pipeline \
  --data-root data/callhome
```

Check generated chunks in:

```text
data/callhome/chunks/
```

### Ingest into PostgreSQL

```powershell
$env:DATABASE_URL = "postgresql://postgres:YOUR_PASSWORD@localhost:5432/YOUR_DATABASE"
python .\ingest_chunks.py `
  --chunks-dir data/callhome/chunks `
  --schema db/schema.sql
```

On macOS/Linux:

```bash
export DATABASE_URL="postgresql://postgres:YOUR_PASSWORD@localhost:5432/YOUR_DATABASE"
python3 ingest_chunks.py \
  --chunks-dir data/callhome/chunks \
  --schema db/schema.sql
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

On macOS/Linux, use the same commands with `python3 -m app.search`.

Search results are printed to the terminal. Persisted source chunks remain in:

```text
data/callhome/chunks/
```

Use `--candidate-count` to control candidates per retriever, `--rrf-k` to
control RRF smoothing, and `--log-level DEBUG` for detailed diagnostics.

### Tests

```powershell
python -m unittest discover -s tests -v
```

On macOS/Linux:

```bash
python3 -m unittest discover -s tests -v
```

Test files are located in:

```text
tests/
```

### Evaluation

```powershell
python -m eval.evaluate `
  --queries data/golden_queries.json `
  --candidate-count 20 `
  --report data/evaluation_report.json
```

On macOS/Linux:

```bash
python3 -m eval.evaluate \
  --queries data/golden_queries.json \
  --candidate-count 20 \
  --report data/evaluation_report.json
```

Check the generated evaluation report at:

```text
data/evaluation_report.json
```

## Current limitations

- The source dataset has 10 conversations, but `call_006` and `call_009` have
  no persisted transcript or chunk output in the current checkout. The
  recorded 621-chunk evaluation therefore covers 8 conversations only.
- ASR errors can affect both lexical matching and semantic relevance.
- The golden set is small and manually labeled.
- Chunk boundaries can split a topic across adjacent chunks.
- The provided speaker labels are trusted ground truth; production unlabeled
  audio would need diarization and would introduce DER-related errors.
- Search currently returns ranked chunks, not transcript-level aggregation or
  answer synthesis.
