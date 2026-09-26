"""CLI for creating searchable chunks from Stage 2 transcript JSON files."""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

from .chunking import chunk_segments, load_aligned_segments


logger = logging.getLogger(__name__)


def process_transcript(
    transcript_path: Path,
    output_path: Path,
    *,
    max_chunk_duration: float = 30.0,
    max_inter_segment_gap: float = 1.0,
) -> None:
    """Load one Stage 2 transcript, chunk it, and persist JSON output."""
    segments = load_aligned_segments(transcript_path)
    source_file = segments[0].source_file if segments else transcript_path.stem + ".wav"
    conversation_id = transcript_path.stem
    chunks = chunk_segments(
        conversation_id,
        source_file,
        segments,
        max_chunk_duration=max_chunk_duration,
        max_inter_segment_gap=max_inter_segment_gap,
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps([chunk.as_dict() for chunk in chunks], indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    logger.info("Persisted %d chunks: %s", len(chunks), output_path)


def main() -> None:
    """Parse CLI arguments and chunk selected persisted transcripts."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-root", type=Path, default=Path("data/callhome"))
    parser.add_argument("--transcripts-dir", type=Path)
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--files", nargs="*", help="Transcript stems, e.g. call_000 call_002")
    parser.add_argument("--max-chunk-duration", type=float, default=30.0)
    parser.add_argument("--max-inter-segment-gap", type=float, default=1.0)
    parser.add_argument("--log-level", choices=["DEBUG", "INFO", "WARNING", "ERROR"], default="INFO")
    args = parser.parse_args()

    logging.basicConfig(
        level=getattr(logging, args.log_level),
        stream=sys.stderr,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )
    transcripts_dir = args.transcripts_dir or args.data_root / "transcripts"
    output_dir = args.output_dir or args.data_root / "chunks"
    paths = sorted(transcripts_dir.glob("*.json"))
    if args.files:
        requested = {Path(name).stem for name in args.files}
        paths = [path for path in paths if path.stem in requested]
    logger.info("Chunking %d transcript files", len(paths))
    for path in paths:
        process_transcript(
            path,
            output_dir / path.name,
            max_chunk_duration=args.max_chunk_duration,
            max_inter_segment_gap=args.max_inter_segment_gap,
        )
    logger.info("Chunking pipeline complete")


if __name__ == "__main__":
    main()
