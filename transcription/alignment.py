"""Deterministic temporal alignment of ASR segments to CALLHOME speakers."""

from __future__ import annotations

import logging
from dataclasses import dataclass

from .metadata import MetadataInterval


logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ASRSegment:
    """One timestamped segment produced by the ASR engine.

    Attributes:
        start_time: ASR segment start in seconds.
        end_time: ASR segment end in seconds.
        text: Transcript text for the segment.
    """

    start_time: float
    end_time: float
    text: str


@dataclass(frozen=True)
class AlignedSegment:
    """A persisted transcript segment with an assigned speaker.

    Attributes:
        source_file: WAV filename associated with the segment.
        speaker_id: Ground-truth CALLHOME speaker label.
        start_time: Segment start in seconds.
        end_time: Segment end in seconds.
        text: Normalized transcript text.
    """

    source_file: str
    speaker_id: str
    start_time: float
    end_time: float
    text: str

    def as_dict(self) -> dict[str, object]:
        """Return the segment in the JSON persistence schema.

        Returns:
            A dictionary containing the five aligned transcript fields.
        """
        return {
            "source_file": self.source_file,
            "speaker_id": self.speaker_id,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "text": self.text,
        }


def overlap_seconds(
    start_a: float, end_a: float, start_b: float, end_b: float
) -> float:
    """Return the temporal intersection of two half-open intervals.

    Args:
        start_a: Start of the first interval in seconds.
        end_a: End of the first interval in seconds.
        start_b: Start of the second interval in seconds.
        end_b: End of the second interval in seconds.

    Returns:
        Positive overlap in seconds, or ``0.0`` when the intervals only touch
        or do not intersect.
    """
    return max(0.0, min(end_a, end_b) - max(start_a, start_b))


def _validate_asr(segment: ASRSegment) -> None:
    """Validate the ordering of one ASR segment.

    Args:
        segment: ASR segment to validate.

    Raises:
        ValueError: If the end timestamp precedes the start timestamp.
    """
    if segment.end_time < segment.start_time:
        raise ValueError("ASR segment has end before start")


def assign_speaker(
    segment: ASRSegment, intervals: list[MetadataInterval]
) -> str | None:
    """Choose the speaker with maximum overlap.

    Ties are resolved by metadata order, then speaker ID, so results do not
    depend on dictionary/set iteration order.

    Args:
        segment: ASR segment requiring a speaker label.
        intervals: Ground-truth CALLHOME speaker intervals.

    Returns:
        The selected speaker ID, or ``None`` when there is no positive overlap.

    Raises:
        ValueError: If the ASR segment has invalid timestamp ordering.
    """
    _validate_asr(segment)
    candidates = [
        (overlap_seconds(segment.start_time, segment.end_time, interval.start_time, interval.end_time), interval)
        for interval in intervals
    ]
    candidates = [(overlap, interval) for overlap, interval in candidates if overlap > 0]
    if not candidates:
        return None
    best_overlap = max(overlap for overlap, _ in candidates)
    tied = [interval for overlap, interval in candidates if overlap == best_overlap]
    speaker = min(tied, key=lambda interval: (interval.order, interval.speaker_id)).speaker_id
    logger.debug(
        "Assigned ASR segment [%.3f, %.3f] to speaker %s with %.3fs overlap",
        segment.start_time,
        segment.end_time,
        speaker,
        best_overlap,
    )
    return speaker


def align_segments(
    source_file: str,
    asr_segments: list[ASRSegment],
    speaker_intervals: list[MetadataInterval],
    *,
    drop_unassigned: bool = True,
) -> list[AlignedSegment]:
    """Assign each ASR segment to one ground-truth speaker interval.

    Each segment is assigned independently using maximum temporal overlap.
    Empty transcript text is ignored. Segments without speaker overlap are
    dropped by default, or reported as an error when ``drop_unassigned`` is
    false.

    Args:
        source_file: WAV filename to store on every output segment.
        asr_segments: Timestamped ASR output in processing order.
        speaker_intervals: CALLHOME ground-truth speaker intervals.
        drop_unassigned: Whether to skip ASR segments with no overlap.

    Returns:
        Aligned transcript segments in the same order as the ASR input.

    Raises:
        ValueError: If an unassigned segment is encountered while
            ``drop_unassigned`` is false.
    """
    aligned: list[AlignedSegment] = []
    unassigned = 0
    for segment in asr_segments:
        speaker = assign_speaker(segment, speaker_intervals)
        if speaker is None:
            unassigned += 1
            if drop_unassigned:
                continue
            raise ValueError(
                f"ASR segment [{segment.start_time}, {segment.end_time}) has no speaker overlap"
            )
        text = segment.text.strip()
        if not text:
            continue
        aligned.append(
            AlignedSegment(source_file, speaker, segment.start_time, segment.end_time, text)
        )
    logger.info(
        "Aligned %d ASR segments into %d speaker segments; %d had no speaker overlap",
        len(asr_segments),
        len(aligned),
        unassigned,
    )
    return aligned
