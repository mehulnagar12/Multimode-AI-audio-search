"""Command-line interface for transcript retrieval."""

from __future__ import annotations

import argparse
import logging
import sys

from .retrieval import search


def main() -> None:
    """Parse search options, execute retrieval, and print ranked results."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("query", help="Natural-language or keyword query")
    parser.add_argument("--mode", choices=["lexical", "semantic", "hybrid"], default="hybrid")
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument("--candidate-count", type=int, default=20)
    parser.add_argument("--rrf-k", type=int, default=60)
    parser.add_argument("--log-level", choices=["DEBUG", "INFO", "WARNING", "ERROR"], default="INFO")
    args = parser.parse_args()
    logger = logging.getLogger(__name__)
    logging.basicConfig(
        level=getattr(logging, args.log_level),
        stream=sys.stderr,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )
    logger.info(
        "CLI search request: mode=%s top_k=%d candidate_count=%d rrf_k=%d",
        args.mode,
        args.top_k,
        args.candidate_count,
        args.rrf_k,
    )
    try:
        results = search(
            args.query,
            args.mode,
            top_k=args.top_k,
            candidate_count=args.candidate_count,
            rrf_k=args.rrf_k,
        )
    except Exception:
        logger.exception("Search failed: mode=%s query=%r", args.mode, args.query)
        raise
    logger.info("Rendering %d results", len(results))
    for rank, result in enumerate(results, start=1):
        logger.debug("Rendering rank=%d chunk_id=%s", rank, result.chunk_id)
        print(
            f"{rank}. score={result.score:.6f} "
            f"file={result.source_file} speaker={result.speaker_id} "
            f"time={result.start_time:.2f}-{result.end_time:.2f}\n"
            f"   {result.text}"
        )


if __name__ == "__main__":
    main()
