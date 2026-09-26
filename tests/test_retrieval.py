"""Deterministic tests for Reciprocal Rank Fusion."""

import unittest

from app.retrieval import SearchResult, rrf_fuse


def result(chunk_id, score=0.0):
    """Create a minimal result for RRF tests."""
    return SearchResult(chunk_id, "call.wav", "A", 0.0, 1.0, chunk_id, score)


class RRFTests(unittest.TestCase):
    """Verify RRF scoring, deduplication, and deterministic ordering."""

    def test_rrf_score_and_deduplication(self):
        """A result appearing in both lists receives both rank contributions."""
        fused = rrf_fuse([[result("a"), result("b")], [result("b"), result("c")]], rrf_k=60)
        self.assertEqual([item.chunk_id for item in fused], ["b", "a", "c"])
        self.assertAlmostEqual(fused[0].score, 1 / 62 + 1 / 61)

    def test_top_k(self):
        """The optional top-k limit is applied after fusion and sorting."""
        fused = rrf_fuse([[result("a"), result("b"), result("c")]], top_k=2)
        self.assertEqual([item.chunk_id for item in fused], ["a", "b"])

    def test_ties_are_deterministic(self):
        """Equal RRF scores are ordered by chunk ID."""
        fused = rrf_fuse([[result("b")], [result("a")]], rrf_k=60)
        self.assertEqual([item.chunk_id for item in fused], ["a", "b"])


if __name__ == "__main__":
    unittest.main()
