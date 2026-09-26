-- Stage 4 minimal transcript-chunk schema.
-- Embedding dimension is centralized in transcription/embedding_config.py.
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS transcript_chunks (
    chunk_id TEXT PRIMARY KEY,
    conversation_id TEXT NOT NULL,
    source_file TEXT NOT NULL,
    speaker_id TEXT NOT NULL,
    start_time DOUBLE PRECISION NOT NULL,
    end_time DOUBLE PRECISION NOT NULL,
    text TEXT NOT NULL,
    embedding vector(384) NOT NULL,
    search_vector TSVECTOR GENERATED ALWAYS AS (
        to_tsvector('simple', coalesce(text, ''))
    ) STORED,
    CONSTRAINT transcript_chunks_valid_time CHECK (end_time >= start_time)
);

CREATE INDEX IF NOT EXISTS transcript_chunks_search_vector_gin
    ON transcript_chunks USING GIN (search_vector);

-- Optional production/scaling index. Keep exact search as the quality baseline.
-- CREATE INDEX transcript_chunks_embedding_hnsw_cosine
--     ON transcript_chunks USING hnsw (embedding vector_cosine_ops);
