"""Deterministic tests for retrieval evaluation metrics."""

import unittest

from app.retrieval import SearchResult
from eval.evaluate import QueryCase, aggregate_metrics, evaluate_method, recall_at_k, reciprocal_rank


def result(chunk_id):
    """Create a minimal deterministic retrieval result."""
    return SearchResult(chunk_id, "call.wav", "A", 0.0, 1.0, chunk_id, 1.0)


class EvaluationMetricTests(unittest.TestCase):
    """Verify Recall@K, MRR, grouping, and macro aggregation."""

    def test_recall_at_k(self):
        """Recall counts unique relevant IDs in the requested prefix."""
        self.assertEqual(recall_at_k(["a", "b", "c"], {"b", "c"}, 1), 0.0)
        self.assertEqual(recall_at_k(["a", "b", "c"], {"b", "c"}, 3), 1.0)
        self.assertEqual(recall_at_k(["b", "b", "c"], {"b", "c"}, 3), 1.0)

    def test_recall_rejects_invalid_inputs(self):
        """Invalid K and empty ground truth are rejected explicitly."""
        with self.assertRaises(ValueError):
            recall_at_k(["a"], {"a"}, 0)
        with self.assertRaises(ValueError):
            recall_at_k(["a"], set(), 1)

    def test_reciprocal_rank(self):
        """MRR is reciprocal of the first relevant rank."""
        self.assertEqual(reciprocal_rank(["x", "b", "a"], {"a", "b"}), 0.5)
        self.assertEqual(reciprocal_rank(["x"], {"a"}), 0.0)

    def test_aggregate_metrics(self):
        """Aggregate metrics are macro averages across queries."""
        metrics = aggregate_metrics([
            {"recall@1": 1.0, "recall@3": 1.0, "recall@5": 1.0, "mrr": 1.0},
            {"recall@1": 0.0, "recall@3": 0.5, "recall@5": 1.0, "mrr": 0.5},
        ])
        self.assertEqual(metrics.query_count, 2)
        self.assertEqual(metrics.recall_at_1, 0.5)
        self.assertEqual(metrics.recall_at_3, 0.75)
        self.assertEqual(metrics.recall_at_5, 1.0)
        self.assertEqual(metrics.mrr, 0.75)

    def test_evaluate_method_with_fixture_search(self):
        """Evaluation uses returned rankings and does not require a database."""
        queries = [QueryCase("first", "keyword", frozenset({"a"})), QueryCase("second", "semantic", frozenset({"c"}))]

        def fixture_search(query, **kwargs):
            return [result("a"), result("b")] if query == "first" else [result("x"), result("c")]

        report = evaluate_method(queries, "lexical", search_fn=fixture_search)
        self.assertEqual(report["overall"]["recall@1"], 0.5)
        self.assertEqual(report["by_type"]["semantic"]["recall@3"], 1.0)

    def test_candidate_count_covers_recall_at_five(self):
        """Evaluation refuses candidate pools too small for Recall@5."""
        with self.assertRaises(ValueError):
            evaluate_method([], "lexical", candidate_count=3, search_fn=lambda *args, **kwargs: [])


if __name__ == "__main__":
    unittest.main()
