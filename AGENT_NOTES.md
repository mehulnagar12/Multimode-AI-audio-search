# Agent Collaboration Notes

## Instructions and scope

- Inspect the locally downloaded CALLHOME data before implementing anything.
- Do not download or modify the dataset during inspection.
- Implement the work incrementally through transcription/alignment, chunking,
  PostgreSQL ingestion, retrieval, and evaluation.
- Keep retrieval and evaluation separate; do not tune retrieval against the
  golden set without an explicit decision.
- Preserve deterministic IDs, timestamps, speaker labels, and tests.

## Decisions accepted

- Use CALLHOME `timestamps_start`, `timestamps_end`, and `speakers` as ground
  truth instead of adding diarization.
- Use local faster-whisper with persisted transcript JSON.
- Use maximum temporal overlap for deterministic speaker assignment.
- Use same-speaker time-based chunks with a 30-second maximum and 1-second
  merge gap.
- Use deterministic SHA-256 chunk IDs.
- Use PostgreSQL, pgvector, and local
  `sentence-transformers/all-MiniLM-L6-v2` embeddings (384 dimensions).
- Use PostgreSQL `tsvector` plus GIN for lexical retrieval and exact cosine
  pgvector search as the quality baseline.
- Use optional HNSW only as a documented scaling path.
- Use RRF with default `k=60`; do not add raw lexical and vector scores.
- Add Recall@1/3/5 and MRR evaluation without implementing golden-set tuning.
- Add standard configurable logging with INFO lifecycle progress and DEBUG
  diagnostics.

## Corrections from real data

- The metadata fields are plural: `timestamps_start` and `timestamps_end`.
- Timestamp values are floating-point seconds and arrays are index-aligned.
- Some intervals overlap, so alignment cannot assume strictly sequential turns.
- A short chunk such as 13 seconds is valid when a speaker boundary occurs;
  30 seconds is a maximum, not a target.
- A second `Tools/data` copy differed from the primary data and was not mixed.
- The PostgreSQL `vector` extension must be installed on the server; the Python
  package alone is insufficient.
- An RRF test expectation was corrected from two rank-1 contributions to the
  actual rank-2-plus-rank-1 calculation.
- Transcription was updated to discover all WAV files and skip existing
  transcript JSON unless `--force` is supplied.
- The golden set was regenerated from actual chunk text and revalidated after
  the chunk directory changed.

## Suggestions and trade-offs

- Keep exact vector search for quality comparison before enabling ANN.
- Use candidate-count experiments and candidate-overlap diagnostics before
  changing hybrid retrieval.
- Treat the current hybrid result cautiously: on the recorded 29-query report,
  hybrid matched semantic retrieval exactly and added no measurable benefit.
- Avoid claiming production latency, throughput, WER, DER, or ANN recall until
  they are measured in the target environment.

## Current verified artifacts

- The current chunk directory contains 621 chunks across 8 files.
- The recorded evaluation report contains 29 queries and candidate_count 20.
- Measured overall Recall@5 is 0.1351 lexical, 0.6730 semantic, and 0.6730
  hybrid; MRR is 0.2069, 0.8632, and 0.8632 respectively.
- Test files cover alignment, chunking, RRF, and evaluation metrics. The full
  suite still needs to be run in a working Python environment.
