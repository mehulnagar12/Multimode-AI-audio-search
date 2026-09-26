# AI Audio Search — Submission

## Solution overview

This project implements a local-first searchable transcript pipeline for
two-speaker conversations. Audio is transcribed locally, aligned to
the dataset's provided speaker intervals, converted into deterministic
speaker-aware chunks, embedded locally, and stored in PostgreSQL with both
full-text and vector-search representations.

The source dataset contains 10 conversations. The current persisted
evaluation artifacts contain 621 chunks from 8 conversations; `call_006` and
`call_009` have audio and metadata but no transcript or chunk output yet. The
golden query set contains 29 manually grounded queries over the current
8-conversation artifact set.

## Engineering design

```text
WAV + metadata
        |
        v
faster-whisper ASR
        |
        v
Temporal speaker alignment
        |
        v
Deterministic speaker-aware chunks
        |
        +--> sentence-transformers embeddings
        |          |
        |          v
        |      PostgreSQL + pgvector
        |
        +--> PostgreSQL tsvector + GIN
                   |
                   v
       lexical / semantic retrieval
                   |
                   v
              RRF fusion
                   |
                   v
              ranked chunks
                   |
                   v
              Recall@K evaluation
```

### Transcription and alignment

`faster-whisper` generates timestamped ASR segments. The transcript is
persisted to JSON so search and evaluation do not retranscribe audio.

Metadata contains timestamp arrays and speaker labels. Each ASR
segment is assigned to the metadata speaker interval with the greatest
temporal overlap. Ties are resolved deterministically by metadata order.
No diarization model is run because speaker annotations are already supplied as
ground truth. For unlabeled production audio, a diarization model such as
pyannote.audio could be inserted before this alignment stage.

### Chunking

Adjacent same-speaker segments are merged when the gap is at most one second
and the resulting chunk is no longer than 30 seconds. Speaker boundaries are
never crossed, and long individual segments are not split by character count.
Chunk IDs are deterministic hashes of the canonical conversation, file,
speaker, timestamps, and text fields.

### Storage and retrieval

PostgreSQL stores the chunk metadata, text, generated `tsvector`, and a
384-dimensional embedding from the local
`sentence-transformers/all-MiniLM-L6-v2` model. The GIN index supports
lexical retrieval using `websearch_to_tsquery` and `ts_rank_cd`. Semantic
retrieval uses exact pgvector cosine distance. HNSW is documented as an
optional scaling index, while exact search remains the quality baseline.

Lexical retrieval keeps the strict query results first and uses a sanitized
token-level `OR` fallback only when the strict result set is smaller than the
requested candidate count. This improves coverage while preserving
deterministic ordering and parameterized SQL.

Hybrid retrieval independently gets lexical and semantic candidate lists and
combines their ranks using Reciprocal Rank Fusion with default `k=60`. Raw
lexical and cosine scores are not added because their scales are not
compatible.

## Rationale

- Local ASR and embeddings avoid sending audio or transcript text to hosted
  services and make repeated search inexpensive.
- Existing speaker intervals are more appropriate than adding a
  second diarization decision to already annotated data.
- Speaker-aware time chunks preserve provenance and make result timestamps
  directly actionable.
- PostgreSQL provides one practical store for metadata, lexical search, and
  vector search.
- Exact vector search provides a trustworthy reference before introducing ANN
  approximations.
- RRF combines ranked evidence without requiring lexical and cosine scores to
  be calibrated onto one scale.

## Success criteria

| Criterion | Achievement |
|---|---|
| Persist timestamped local transcripts | Implemented; transcript JSON is written per WAV |
| Preserve provided speaker information | Implemented with temporal-overlap alignment |
| Produce deterministic speaker-aware chunks | Implemented and tested |
| Store text, metadata, and embeddings in PostgreSQL | Implemented; an earlier ingestion run verified 237 rows and 384-dimensional vectors. The current 621-chunk artifact set requires a new full ingestion run for matching DB coverage. |
| Support lexical, semantic, and hybrid retrieval | Implemented with CLI output containing file, speaker, timestamps, text, score, and rank |
| Evaluate independently with Recall@1/3/5 | Implemented and run against 29 queries |
| Avoid unmeasured claims | Followed; production latency and speech-quality metrics remain unmeasured |

## Measured evaluation

The latest report uses 29 queries and 20 candidates per retriever.
Recall values are macro-averages across queries.

| Method | Recall@1 | Recall@3 | Recall@5 | MRR |
|---|---:|---:|---:|---:|
| Lexical | 0.1494 | 0.2730 | 0.3218 | 0.4466 |
| Semantic | 0.2713 | 0.5655 | 0.6730 | 0.8632 |
| Hybrid | 0.2385 | 0.4552 | 0.5626 | 0.7793 |

The schema and retrieval code use the `simple` text-search configuration,
which keeps stop words and does not stem terms, while strict
`websearch_to_tsquery` requires every query word to match. The new token-level
`OR` fallback improved lexical retrieval but introduced noisier candidates
into RRF, so hybrid currently underperforms semantic retrieval.
The semantic MRR of 0.8632 alongside Recall@1 of 0.2713 is consistent. MRR
only measures the first relevant result's rank; Recall@1 measures how many of
all relevant chunks appear in the first result. Twenty-eight of 29 queries
have multiple relevant chunks, so the first relevant chunk can rank highly
even when other relevant chunks are lower.

## Outputs

| Output | Location | Verified result |
|---|---|---|
| Persisted ASR transcripts | `data/callhome/transcripts/` | Timestamped transcript JSON files produced by the transcription pipeline; existing files are skipped on later runs unless `--force` is used. |
| Speaker-aware chunks | `data/callhome/chunks/` | 621 chunks across 8 conversation files, with deterministic IDs, speaker IDs, timestamps, and text. `call_006` and `call_009` are not present in this output directory yet. |
| Golden evaluation queries | `data/golden_queries.json` | 29 manually grounded queries whose relevant IDs were checked against actual chunk text. |
| Evaluation report | `data/evaluation_report.json` and `data/evaluation_dashboard_latest.html` | Latest lexical, semantic, and hybrid Recall@1/3/5 and MRR results. |
| PostgreSQL chunk storage | `transcript_chunks` table | An ingestion verification run stored 237 chunks with 384-dimensional embeddings, zero null speakers, and zero invalid timestamps. This is an earlier recorded ingestion result, not a claim that all 621 current chunks were re-ingested. |

Search output is printed to the terminal by `app.search`. Each ranked result
includes the source file, speaker, start and end times, transcript text, and
final score/rank. The database stores the ingested chunk and embedding data;
it is not written to a repository output file.

## Limitations

- The source dataset contains 10 conversations, but the current transcript and
  chunk outputs contain only 8. The missing conversations are `call_006` and
  `call_009`; rerunning transcription and chunking will update the artifacts
  and invalidate the recorded counts and evaluation coverage.
- ASR recognition errors affect both exact keyword and semantic retrieval.
- The golden set is small and manually labeled, so results are directional.
- Topic boundaries can split relevant context across chunks.
- Hybrid retrieval currently does not outperform semantic retrieval.
- The database must have the pgvector server extension installed separately
  from the Python package.

Additional production metrics should include p50/p95/p99 query latency,
throughput, ingestion throughput, embedding and transcription latency, index
build time, DB/index size, error rate, WER, DER when diarization is used, and
ANN recall against exact search.

## Coding-agent disclosure

Coding agents were used throughout the project. The agent was directed through
stage-specific prompts and constraints, including:

- inspect the local dataset and verify metadata before implementation;
- do not download or modify the dataset during inspection;
- use existing speaker intervals instead of adding diarization;
- persist transcripts and deterministic chunks;
- use PostgreSQL, pgvector, local sentence-transformers embeddings, and RRF;
- add focused deterministic tests and visible logging;
- create evaluation queries only from actual transcript chunk content;
- do not fabricate measurements or tune retrieval against the golden set
  without diagnosis.

see the [agent notes](AGENT_NOTES.md)

The agent's suggestions and corrections were reviewed during development. The
accepted decisions included 30-second maximum chunks, one-second merge gaps,
maximum-overlap speaker assignment, 384-dimensional local embeddings, exact
cosine search as a baseline, optional HNSW, and RRF `k=60`. Corrections after
real-data inspection included handling plural timestamp field names, avoiding a
conflicting duplicate dataset copy, recognizing that 30 seconds is a maximum
rather than a target, installing pgvector on the PostgreSQL server, fixing an
RRF test expectation, skipping existing transcripts, and revalidating golden
IDs after chunks changed.

The reusable `application-logging` and `test-case-writing` skills were used to
review logging behavior and strengthen deterministic test coverage.
