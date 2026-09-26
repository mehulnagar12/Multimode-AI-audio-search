# CALLHOME Local Hybrid Search PoC — Submission

## Solution overview

This project implements a local-first searchable transcript pipeline for
CALLHOME two-speaker conversations. Audio is transcribed locally, aligned to
the dataset's provided speaker intervals, converted into deterministic
speaker-aware chunks, embedded locally, and stored in PostgreSQL with both
full-text and vector-search representations.

The current persisted evaluation artifacts contain 621 chunks from 8
conversations. The golden query set contains 29 manually grounded queries.

## Engineering design

```text
WAV + CALLHOME metadata
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

CALLHOME metadata contains timestamp arrays and speaker labels. Each ASR
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

Hybrid retrieval independently gets lexical and semantic candidate lists and
combines their ranks using Reciprocal Rank Fusion with default `k=60`. Raw
lexical and cosine scores are not added because their scales are not
compatible.

## Rationale

- Local ASR and embeddings avoid sending audio or transcript text to hosted
  services and make repeated search inexpensive.
- Existing CALLHOME speaker intervals are more appropriate than adding a
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
| Store text, metadata, and embeddings in PostgreSQL | Implemented; an earlier ingestion run verified 237 rows and 384-dimensional vectors |
| Support lexical, semantic, and hybrid retrieval | Implemented with CLI output containing file, speaker, timestamps, text, score, and rank |
| Evaluate independently with Recall@1/3/5 | Implemented and run against 29 queries |
| Avoid unmeasured claims | Followed; production latency and speech-quality metrics remain unmeasured |

## Measured evaluation

The recorded report uses 29 queries and 20 candidates per retriever.
Recall values are macro-averages across queries.

| Method | Recall@1 | Recall@3 | Recall@5 | MRR |
|---|---:|---:|---:|---:|
| Lexical | 0.0977 | 0.1351 | 0.1351 | 0.2069 |
| Semantic | 0.2713 | 0.5655 | 0.6730 | 0.8632 |
| Hybrid | 0.2713 | 0.5655 | 0.6730 | 0.8632 |

Hybrid did not provide measurable improvement over semantic retrieval in this
run. The likely issue is lexical candidate coverage: several queries describe
information distributed across multiple chunks, while PostgreSQL full-text
matching requires the query terms to be present in an individual chunk. The
next diagnostic should inspect candidate-list overlap and relevant IDs before
changing retrieval behavior.

## Limitations

- The current chunk set contains 8 files rather than the original 10-file
  target.
- ASR recognition errors affect both exact keyword and semantic retrieval.
- The golden set is small and manually labeled, so results are directional.
- Topic boundaries can split relevant context across chunks.
- Hybrid retrieval currently does not outperform semantic retrieval.
- The database must have the pgvector server extension installed separately
  from the Python package.
- Tests are implemented, but a complete test run was not verified in the
  agent environment because its Python launcher referenced a missing Python
  executable.

Additional production metrics should include p50/p95/p99 query latency,
throughput, ingestion throughput, embedding and transcription latency, index
build time, DB/index size, error rate, WER, DER when diarization is used, and
ANN recall against exact search.

## Coding-agent disclosure

Coding agents were used throughout the project. The agent was directed through
stage-specific prompts and constraints, including:

- inspect the local dataset and verify metadata before implementation;
- do not download or modify the dataset during inspection;
- use existing CALLHOME speaker intervals instead of adding diarization;
- persist transcripts and deterministic chunks;
- use PostgreSQL, pgvector, local sentence-transformers embeddings, and RRF;
- add focused deterministic tests and visible logging;
- create evaluation queries only from actual transcript chunk content;
- do not fabricate measurements or tune retrieval against the golden set
  without diagnosis.

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
