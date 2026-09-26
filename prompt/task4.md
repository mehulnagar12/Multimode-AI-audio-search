# Task 4 — PostgreSQL and pgvector ingestion

Implement storage and ingestion for the chunks from Stage 3.

Use:

* PostgreSQL
* pgvector
* sentence-transformers
* local embedding generation

Requirements:

1. Create the minimal PostgreSQL schema for transcript chunks.
2. Store:

   * chunk_id
   * conversation_id
   * source_file
   * speaker_id
   * start_time
   * end_time
   * text
   * embedding
3. Add PostgreSQL full-text support:

   * tsvector
   * GIN index
4. Add pgvector support.
5. Use a lightweight established sentence-transformers retrieval model.
6. Centralize model name/config.
7. Generate embeddings locally during ingestion.
8. Do not regenerate embeddings during search except the query embedding.
9. Use cosine similarity/distance consistently.
10. Keep exact vector search available as the quality baseline.
11. Add optional HNSW indexing for production/scaling discussion.

Do NOT call PostgreSQL ts_rank/ts_rank_cd BM25.

Use parameterized SQL.

DB credentials/config must come from environment variables.

Do not implement RRF/evaluation yet.

Run ingestion on the selected dataset and verify:

* expected chunks are stored
* embeddings have correct dimensions
* speaker/timestamp metadata survived ingestion

Report verification results concisely.
