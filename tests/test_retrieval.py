"""Deterministic tests for Reciprocal Rank Fusion."""

import unittest

from app.retrieval import SearchResult, lexical_search, rrf_fuse


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


class FakeCursor:
    """Small deterministic cursor fixture for lexical fallback tests."""

    def __init__(self, rows):
        self.rows = rows

    def fetchall(self):
        return self.rows


class FakeConnection:
    """Return predefined strict and relaxed lexical result rows."""

    def __init__(self, strict_rows, relaxed_rows):
        self.strict_rows = strict_rows
        self.relaxed_rows = relaxed_rows
        self.calls = []

    def execute(self, sql, params):
        self.calls.append((sql, params))
        if "websearch_to_tsquery" not in sql:
            return FakeCursor(self.relaxed_rows)
        return FakeCursor(self.strict_rows)


class LexicalFallbackTests(unittest.TestCase):
    """Verify strict lexical search and deterministic OR fallback behavior."""

    def test_fallback_appends_new_results_after_strict_results(self):
        strict = [("a", "call.wav", "A", 0.0, 1.0, "alpha", 0.9)]
        relaxed = [("b", "call.wav", "B", 1.0, 2.0, "beta", 0.4)]
        connection = FakeConnection(strict, relaxed)

        results = lexical_search(connection, "alpha beta", candidate_count=2)

        self.assertEqual([item.chunk_id for item in results], ["a", "b"])
        self.assertEqual(len(connection.calls), 2)
        self.assertEqual(connection.calls[1][1][0], "alpha | beta")
        self.assertEqual(connection.calls[1][1][2], ["a"])

    def test_fallback_is_not_used_when_strict_results_fill_limit(self):
        strict = [
            ("a", "call.wav", "A", 0.0, 1.0, "alpha", 0.9),
            ("b", "call.wav", "B", 1.0, 2.0, "beta", 0.8),
        ]
        connection = FakeConnection(strict, [])

        results = lexical_search(connection, "alpha beta", candidate_count=2)

        self.assertEqual([item.chunk_id for item in results], ["a", "b"])
        self.assertEqual(len(connection.calls), 1)

    def test_fallback_skips_queries_without_searchable_tokens(self):
        connection = FakeConnection([], [])

        results = lexical_search(connection, "---", candidate_count=2)

        self.assertEqual(results, [])
        self.assertEqual(len(connection.calls), 1)


if __name__ == "__main__":
    unittest.main()
