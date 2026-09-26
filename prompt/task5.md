# Task 5 — Retrieval and RRF

Implement retrieval over the PostgreSQL chunks.

Support three modes:

1. lexical
2. semantic
3. hybrid

Lexical:

* PostgreSQL full-text search
* websearch_to_tsquery or plainto_tsquery
* ts_rank_cd
* use the existing GIN index

Semantic:

* locally embed only the query
* pgvector cosine search
* retrieve top N candidates

Hybrid:

* retrieve top N lexical candidates
* retrieve top N semantic candidates
* combine using Reciprocal Rank Fusion

RRF:

score(d) = Σ 1 / (k + rank_i(d))

Default k = 60.

Make k and candidate count configurable.

Deduplicate by chunk_id.

Do NOT directly add raw lexical and cosine scores.

Provide a minimal CLI:

python -m app.search "query" --top-k 5

Every result must display:

* source_file
* speaker
* start_time
* end_time
* transcript text
* final score/rank

Allow lexical, semantic and hybrid modes to be called independently because we will compare them during evaluation.

Add deterministic unit tests for RRF.

Run several real searches and report results briefly.

Do not implement golden evaluation yet.

