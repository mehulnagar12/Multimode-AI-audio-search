"""Generate local embeddings and ingest Stage 3 chunks into PostgreSQL."""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

from transcription.db import apply_schema, connect_from_environment, insert_chunks, verify_storage
from transcription.embedding_config import DEFAULT_EMBEDDING_CONFIG
from transcription.embeddings import LocalEmbedder


logger = logging.getLogger(__name__)


def load_chunk_records(chunks_dir: Path) -> list[dict[str, object]]:
    """Load all Stage 3 JSON chunk records from a directory."""
    records: list[dict[str, object]] = []
    for path in sorted(chunks_dir.glob("*.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        records.extend(data)
        logger.info("Loaded %d chunks from %s", len(data), path)
    return records


def main() -> None:
    """Run schema setup, local embedding generation, insertion, and checks."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--chunks-dir", type=Path, default=Path("data/callhome/chunks"))
    parser.add_argument("--schema", type=Path, default=Path("db/schema.sql"))
    parser.add_argument("--log-level", choices=["DEBUG", "INFO", "WARNING", "ERROR"], default="INFO")
    args = parser.parse_args()
    logging.basicConfig(
        level=getattr(logging, args.log_level),
        stream=sys.stderr,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )

    chunks = load_chunk_records(args.chunks_dir)
    if not chunks:
        raise RuntimeError(f"No chunk JSON files found in {args.chunks_dir}")
    logger.info("Using embedding model %s", DEFAULT_EMBEDDING_CONFIG.model_name)
    embedder = LocalEmbedder()
    embeddings = embedder.encode([str(chunk["text"]) for chunk in chunks])

    with connect_from_environment() as connection:
        apply_schema(connection, args.schema)
        insert_chunks(connection, chunks, embeddings)
        verification = verify_storage(connection, len(chunks))
    logger.info("Final verification: %s", verification)


if __name__ == "__main__":
    main()
