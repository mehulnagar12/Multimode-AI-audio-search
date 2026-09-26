"""Parsing and validation for the CALLHOME metadata schema."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any


logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class MetadataInterval:
    """One ground-truth CALLHOME speaker interval.

    Attributes:
        start_time: Interval start in seconds from the beginning of the WAV.
        end_time: Interval end in seconds from the beginning of the WAV.
        speaker_id: CALLHOME speaker label, such as ``A`` or ``B``.
        order: Original zero-based position in the metadata arrays. This is
            used as a deterministic tie-breaker during alignment.
    """

    start_time: float
    end_time: float
    speaker_id: str
    order: int


def load_metadata(path: str | Path, audio_name: str | None = None) -> list[MetadataInterval]:
    """Load and validate the verified CALLHOME plural timestamp schema.

    Intervals are half-open [start, end), which makes boundary behavior
    deterministic: two intervals touching at one instant have zero overlap.

    Args:
        path: JSON metadata file to read.
        audio_name: Optional WAV filename that must match ``source_file``.

    Returns:
        Metadata intervals in their original JSON order.

    Raises:
        ValueError: If required fields are missing, array lengths differ,
            ``source_file`` does not match, or an interval is invalid.
        json.JSONDecodeError: If the file is not valid JSON.
    """
    path = Path(path)
    data: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
    required = {"source_file", "timestamps_start", "timestamps_end", "speakers"}
    missing = required.difference(data)
    if missing:
        raise ValueError(f"{path}: missing metadata fields: {sorted(missing)}")

    if audio_name is not None and data["source_file"] != audio_name:
        raise ValueError(
            f"{path}: source_file={data['source_file']!r} does not match {audio_name!r}"
        )

    starts = data["timestamps_start"]
    ends = data["timestamps_end"]
    speakers = data["speakers"]
    lengths = {len(starts), len(ends), len(speakers)}
    if len(lengths) != 1:
        raise ValueError(
            f"{path}: timestamp/speaker lengths differ: "
            f"start={len(starts)}, end={len(ends)}, speakers={len(speakers)}"
        )

    intervals: list[MetadataInterval] = []
    for index, (start, end, speaker) in enumerate(zip(starts, ends, speakers)):
        start = float(start)
        end = float(end)
        if end < start:
            raise ValueError(f"{path}: interval {index} has end before start")
        if not isinstance(speaker, str) or not speaker:
            raise ValueError(f"{path}: interval {index} has invalid speaker id")
        intervals.append(MetadataInterval(start, end, speaker, index))
    logger.info("Loaded metadata: %s intervals from %s", len(intervals), path)
    return intervals
