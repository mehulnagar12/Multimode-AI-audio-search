"""Focused unit tests for CALLHOME metadata and speaker alignment."""

import json
import tempfile
import unittest
from pathlib import Path

from transcription.alignment import ASRSegment, align_segments, assign_speaker, overlap_seconds
from transcription.metadata import MetadataInterval, load_metadata


class AlignmentTests(unittest.TestCase):
    def test_metadata_parsing_and_length_validation(self):
        """Verify valid CALLHOME metadata becomes indexed intervals."""
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "call.json"
            path.write_text(json.dumps({
                "source_file": "call.wav",
                "timestamps_start": [0.0, 1.0],
                "timestamps_end": [1.0, 2.0],
                "speakers": ["A", "B"],
            }))
            intervals = load_metadata(path, "call.wav")
            self.assertEqual([(i.start_time, i.end_time, i.speaker_id) for i in intervals], [(0.0, 1.0, "A"), (1.0, 2.0, "B")])

    def test_overlap_and_touching_boundary(self):
        """Verify positive overlap and zero overlap at a touching boundary."""
        self.assertEqual(overlap_seconds(0, 1, 1, 2), 0.0)
        self.assertEqual(overlap_seconds(0, 2, 1, 3), 1.0)

    def test_maximum_overlap_assignment(self):
        """Verify speaker assignment selects the interval with most overlap."""
        intervals = load_metadata_from_values([(0, 4, "A"), (3, 10, "B")])
        self.assertEqual(assign_speaker(ASRSegment(2, 5, "hello"), intervals), "A")
        self.assertEqual(assign_speaker(ASRSegment(4, 8, "world"), intervals), "B")

    def test_deterministic_tie_uses_metadata_order(self):
        """Verify equal-overlap assignment uses stable metadata ordering."""
        intervals = load_metadata_from_values([(0, 5, "B"), (5, 10, "A")])
        self.assertEqual(assign_speaker(ASRSegment(4, 6, "tie"), intervals), "B")

    def test_unassigned_segment_is_dropped(self):
        """Verify segments outside all speaker intervals are omitted."""
        intervals = load_metadata_from_values([(0, 1, "A")])
        self.assertEqual(align_segments("call.wav", [ASRSegment(2, 3, "outside")], intervals), [])


def load_metadata_from_values(values):
    """Build typed metadata intervals for unit-test scenarios."""
    return [
        MetadataInterval(start, end, speaker, index)
        for index, (start, end, speaker) in enumerate(values)
    ]


if __name__ == "__main__":
    unittest.main()
