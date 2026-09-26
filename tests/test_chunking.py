"""Focused tests for deterministic, speaker-aware transcript chunking."""

import unittest

from transcription.alignment import AlignedSegment
from transcription.chunking import chunk_segments, make_chunk_id


def segment(start, end, speaker, text, source="call_000.wav"):
    """Create a compact aligned segment for a chunking test."""
    return AlignedSegment(source, speaker, start, end, text)


class ChunkingTests(unittest.TestCase):
    """Verify chunk boundaries, timestamps, and stable identifiers."""

    def test_same_speaker_merging(self):
        """Adjacent same-speaker segments merge into one text window."""
        chunks = chunk_segments("call_000", "call_000.wav", [segment(0, 2, "A", "hello"), segment(2.2, 5, "A", "world")])
        self.assertEqual(len(chunks), 1)
        self.assertEqual(chunks[0].text, "hello world")

    def test_speaker_boundary(self):
        """A speaker change always creates a new chunk."""
        chunks = chunk_segments("call_000", "call_000.wav", [segment(0, 2, "A", "hello"), segment(2, 4, "B", "reply")])
        self.assertEqual([chunk.speaker_id for chunk in chunks], ["A", "B"])

    def test_timestamps_are_preserved(self):
        """Merged chunks use the first start and final end timestamps."""
        chunks = chunk_segments("call_000", "call_000.wav", [segment(10, 12, "A", "one"), segment(12.5, 15, "A", "two")])
        self.assertEqual((chunks[0].start_time, chunks[0].end_time), (10, 15))

    def test_chunk_ids_are_deterministic(self):
        """Identical canonical chunk inputs produce identical IDs."""
        first = make_chunk_id("call_000", "call_000.wav", "A", 0, 2, "hello")
        second = make_chunk_id("call_000", "call_000.wav", "A", 0, 2, "hello")
        self.assertEqual(first, second)

    def test_duration_limit_and_long_segment(self):
        """Merging stops at the duration limit without splitting a long segment."""
        chunks = chunk_segments("call_000", "call_000.wav", [segment(0, 20, "A", "long"), segment(20, 35, "A", "next")], max_chunk_duration=30)
        self.assertEqual(len(chunks), 2)
        self.assertEqual((chunks[1].start_time, chunks[1].end_time), (20, 35))

    def test_empty_input(self):
        """Empty aligned input produces no chunks."""
        self.assertEqual(chunk_segments("call_000", "call_000.wav", []), [])

    def test_gap_prevents_merging(self):
        """A gap larger than the configured threshold creates a new chunk."""
        chunks = chunk_segments("call_000", "call_000.wav", [segment(0, 1, "A", "one"), segment(3, 4, "A", "two")])
        self.assertEqual(len(chunks), 2)


if __name__ == "__main__":
    unittest.main()
