"""Speaker-aware, time-based chunking for aligned CALLHOME transcripts."""

from __future__ import annotations

import hashlib
import json
import logging
from dataclasses import dataclass
from pathlib import Path

from .alignment import AlignedSegment


logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class TranscriptChunk:
    """One searchable, speaker-homogeneous transcript chunk.

    Attributes:
        chunk_id: Deterministic SHA-256-based identifier.
        conversation_id: Stable conversation identifier, normally the WAV stem.
        source_file: Original WAV filename.
        speaker_id: Single CALLHOME speaker label for the entire chunk.
        start_time: First segment start time in seconds.
        end_time: Last segment end time in seconds.
        text: Space-joined transcript text.
    """

    chunk_id: str
    conversation_id: str
    source_file: str
    speaker_id: str
    start_time: float
    end_time: float
    text: str

    def as_dict(self) -> dict[str, object]:
        """Return this chunk in the persisted JSON schema."""
        return {
            "chunk_id": self.chunk_id,
            "conversation_id": self.conversation_id,
            "source_file": self.source_file,
            "speaker_id": self.speaker_id,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "text": self.text,
        }


def _canonical_chunk_payload(
    conversation_id: str,
    source_file: str,
    speaker_id: str,
    start_time: float,
    end_time: float,
    text: str,
) -> str:
    """Serialize chunk identity fields deterministically for hashing."""
    payload = {
        "conversation_id": conversation_id,
        "source_file": source_file,
        "speaker_id": speaker_id,
        "start_time": round(start_time, 6),
        "end_time": round(end_time, 6),
        "text": text,
    }
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def make_chunk_id(
    conversation_id: str,
    source_file: str,
    speaker_id: str,
    start_time: float,
    end_time: float,
    text: str,
) -> str:
    """Create a stable ID from the canonical chunk content.

    The ID is independent of Python object identity, dictionary ordering, and
    process execution order. It changes only when one of the chunk identity
    fields changes.
    """
    payload = _canonical_chunk_payload(
        conversation_id, source_file, speaker_id, start_time, end_time, text
    )
    digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()
    return f"chunk_{digest[:20]}"


def _validate_segment(segment: AlignedSegment) -> None:
    """Validate timestamps and required fields on an aligned segment."""
    if segment.end_time < segment.start_time:
        raise ValueError("Aligned segment has end before start")
    if not segment.speaker_id:
        raise ValueError("Aligned segment has an empty speaker_id")


def _build_chunk(
    conversation_id: str,
    source_file: str,
    speaker_id: str,
    segments: list[AlignedSegment],
) -> TranscriptChunk:
    """Build one chunk from already-compatible same-speaker segments."""
    start_time = segments[0].start_time
    end_time = segments[-1].end_time
    text = " ".join(segment.text.strip() for segment in segments if segment.text.strip())
    return TranscriptChunk(
        chunk_id=make_chunk_id(
            conversation_id, source_file, speaker_id, start_time, end_time, text
        ),
        conversation_id=conversation_id,
        source_file=source_file,
        speaker_id=speaker_id,
        start_time=start_time,
        end_time=end_time,
        text=text,
    )


def chunk_segments(
    conversation_id: str,
    source_file: str,
    segments: list[AlignedSegment],
    *,
    max_chunk_duration: float = 30.0,
    max_inter_segment_gap: float = 1.0,
) -> list[TranscriptChunk]:
    """Merge aligned segments into speaker-aware time-based chunks.

    Segments are ordered by start time, end time, and original input position.
    A segment is merged only when it has the same speaker as the current
    chunk, its gap from the current chunk is within ``max_inter_segment_gap``,
    and the resulting duration is at most ``max_chunk_duration``. A long
    individual segment is kept intact rather than split by characters.

    Args:
        conversation_id: Stable identifier for the conversation.
        source_file: Original WAV filename.
        segments: Stage 2 aligned transcript segments.
        max_chunk_duration: Maximum duration of a merged chunk in seconds.
        max_inter_segment_gap: Largest gap eligible for same-speaker merging.

    Returns:
        Deterministically ordered transcript chunks. Empty input returns an
        empty list.

    Raises:
        ValueError: If a duration or gap configuration is non-positive, or an
            input segment has invalid timestamps or speaker data.
    """
    if max_chunk_duration <= 0:
        raise ValueError("max_chunk_duration must be positive")
    if max_inter_segment_gap < 0:
        raise ValueError("max_inter_segment_gap cannot be negative")
    if not segments:
        return []

    indexed = list(enumerate(segments))
    for _, segment in indexed:
        _validate_segment(segment)
    ordered = [segment for _, segment in sorted(indexed, key=lambda item: (item[1].start_time, item[1].end_time, item[0]))]

    chunks: list[TranscriptChunk] = []
    current: list[AlignedSegment] = []
    for segment in ordered:
        if not segment.text.strip():
            continue
        if not current:
            current = [segment]
            continue

        previous = current[-1]
        candidate_duration = segment.end_time - current[0].start_time
        gap = max(0.0, segment.start_time - previous.end_time)
        can_merge = (
            segment.speaker_id == previous.speaker_id
            and gap <= max_inter_segment_gap
            and candidate_duration <= max_chunk_duration
        )
        if can_merge:
            current.append(segment)
        else:
            chunks.append(_build_chunk(conversation_id, source_file, current[0].speaker_id, current))
            current = [segment]

    if current:
        chunks.append(_build_chunk(conversation_id, source_file, current[0].speaker_id, current))

    logger.info(
        "Chunked %d aligned segments into %d chunks for %s",
        len(ordered),
        len(chunks),
        source_file,
    )
    return chunks


def load_aligned_segments(path: str | Path) -> list[AlignedSegment]:
    """Load persisted Stage 2 aligned segments from a JSON array."""
    records = json.loads(Path(path).read_text(encoding="utf-8"))
    return [
        AlignedSegment(
            source_file=record["source_file"],
            speaker_id=record["speaker_id"],
            start_time=float(record["start_time"]),
            end_time=float(record["end_time"]),
            text=record["text"],
        )
        for record in records
    ]
