"""CLI for persisted CALLHOME transcription and speaker alignment."""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

from .alignment import align_segments
from .metadata import load_metadata
from .transcribe import FasterWhisperTranscriber


logger = logging.getLogger(__name__)


def process_file(audio_path: Path, metadata_path: Path, output_path: Path, transcriber) -> None:
    """Transcribe, align, and persist one CALLHOME conversation.

    Args:
        audio_path: Input WAV file.
        metadata_path: Matching CALLHOME metadata JSON file.
        output_path: JSON file receiving aligned transcript segments.
        transcriber: Object exposing ``transcribe(audio_path)``.

    The output directory is created when needed. Existing output at the same
    path is overwritten with the newly generated aligned transcript.
    """
    logger.info("Starting file: %s", audio_path.name)
    intervals = load_metadata(metadata_path, audio_path.name)
    asr_segments = transcriber.transcribe(audio_path)
    aligned = align_segments(audio_path.name, asr_segments, intervals)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps([segment.as_dict() for segment in aligned], indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    logger.info("Persisted %d aligned segments: %s", len(aligned), output_path)


def main() -> None:
    """Parse CLI arguments and process the selected CALLHOME files.

    The command configures console logging, loads the local ASR model, and
    writes one persisted transcript JSON file per input WAV.
    """
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-root", type=Path, default=Path("data/callhome"))
    parser.add_argument("--model-path", type=Path, required=True)
    parser.add_argument(
        "--files",
        nargs="*",
        help="Specific WAV filenames; when omitted, process every WAV in audio/",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Retranscribe files whose persisted transcript JSON already exists",
    )
    parser.add_argument("--device", default="cpu")
    parser.add_argument("--compute-type", default="int8")
    parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        default="INFO",
        help="Logging verbosity (default: INFO)",
    )
    args = parser.parse_args()

    logging.basicConfig(
        level=getattr(logging, args.log_level),
        stream=sys.stderr,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )
    logger.info("Starting CALLHOME transcription and speaker alignment")
    logger.info("Data root: %s", args.data_root)
    audio_dir = args.data_root / "audio"
    transcript_dir = args.data_root / "transcripts"
    if args.files:
        audio_paths = [audio_dir / filename for filename in args.files]
    else:
        audio_paths = sorted(audio_dir.glob("*.wav"))
    logger.info("Files discovered: %d", len(audio_paths))
    if args.force:
        logger.info("Force mode enabled: existing transcripts will be replaced")

    transcriber = None
    processed = 0
    skipped = 0
    for audio in audio_paths:
        filename = audio.name
        metadata = args.data_root / "metadata" / f"{audio.stem}.json"
        output = transcript_dir / f"{audio.stem}.json"
        if output.exists() and not args.force:
            logger.info("Skipping existing transcript: %s", output)
            skipped += 1
            continue
        if not metadata.exists():
            raise FileNotFoundError(f"Metadata file not found for {filename}: {metadata}")
        if transcriber is None:
            transcriber = FasterWhisperTranscriber(args.model_path, args.device, args.compute_type)
        process_file(audio, metadata, output, transcriber)
        processed += 1
    logger.info("Transcription summary: processed=%d skipped=%d", processed, skipped)
    logger.info("Pipeline complete")


if __name__ == "__main__":
    main()
