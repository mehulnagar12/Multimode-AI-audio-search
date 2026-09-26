# Task 3 — Speaker-aware transcript chunking

Implement searchable transcript chunking using the aligned segments from Stage 2.

Requirements:

* chunks must be speaker-aware
* never combine different speakers
* preserve timestamps
* merge adjacent short same-speaker segments when appropriate
* avoid arbitrary character-only splitting
* keep chunk size/configuration simple

Each chunk must contain:

* chunk_id
* conversation_id
* source_file
* speaker_id
* start_time
* end_time
* text

chunk_id must be stable/deterministic across runs so it can later be referenced by golden evaluation labels.

Add tests for:

* same-speaker merging
* speaker boundaries
* timestamps
* deterministic chunk IDs
* empty/edge cases

Do not implement database/search/embeddings yet.

Run tests and briefly report results.

