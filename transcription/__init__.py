"""CALLHOME transcription and speaker-alignment utilities.

The package exposes the core metadata parser, timestamp-overlap functions,
and alignment data structures used by the Stage 2 pipeline.
"""

from .alignment import ASRSegment, MetadataInterval, align_segments, overlap_seconds
from .chunking import TranscriptChunk, chunk_segments, make_chunk_id
from .metadata import load_metadata

__all__ = [
    "ASRSegment",
    "MetadataInterval",
    "TranscriptChunk",
    "align_segments",
    "chunk_segments",
    "load_metadata",
    "make_chunk_id",
    "overlap_seconds",
]
