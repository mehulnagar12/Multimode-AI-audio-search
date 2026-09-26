"""Evaluate lexical, semantic, and hybrid retrieval against golden queries."""

from __future__ import annotations

import argparse
import json
import logging
import sys
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Iterable

from app.retrieval import SearchResult, search


logger = logging.getLogger(__name__)
K_VALUES = (1, 3, 5)
METHODS = ("lexical", "semantic", "hybrid")


@dataclass(frozen=True)
class QueryCase:
    """One golden evaluation query and its manually labeled chunks."""

    query: str
    query_type: str
    relevant_chunk_ids: frozenset[str]


@dataclass(frozen=True)
class MethodMetrics:
    """Aggregate metrics for one retrieval method and query group."""

    query_count: int
    recall_at_1: float
    recall_at_3: float
    recall_at_5: float
    mrr: float

    def as_dict(self) -> dict[str, object]:
        """Return metrics using the JSON report field names."""
        return {
            "query_count": self.query_count,
            "recall@1": self.recall_at_1,
            "recall@3": self.recall_at_3,
            "recall@5": self.recall_at_5,
            "mrr": self.mrr,
        }


def load_queries(path: str | Path) -> list[QueryCase]:
    """Load and validate golden queries from JSON."""
    records = json.loads(Path(path).read_text(encoding="utf-8"))
    queries: list[QueryCase] = []
    for index, record in enumerate(records):
        if not record.get("query") or record.get("type") not in {"keyword", "semantic", "mixed"}:
            raise ValueError(f"Invalid golden query at index {index}")
        ids = frozenset(record.get("relevant_chunk_ids", []))
        if not ids:
            raise ValueError(f"Golden query at index {index} has no relevant chunks")
        queries.append(QueryCase(record["query"], record["type"], ids))
    return queries


def recall_at_k(retrieved_ids: Iterable[str], relevant_ids: set[str] | frozenset[str], k: int) -> float:
    """Calculate Recall@K for one query.

    Recall is the fraction of all labeled relevant chunks present in the first
    K retrieved results. Duplicate retrieved IDs do not inflate the metric.
    """
    if k <= 0:
        raise ValueError("k must be positive")
    relevant = set(relevant_ids)
    if not relevant:
        raise ValueError("relevant_ids must not be empty")
    return len(set(list(retrieved_ids)[:k]) & relevant) / len(relevant)


def reciprocal_rank(retrieved_ids: Iterable[str], relevant_ids: set[str] | frozenset[str]) -> float:
    """Return reciprocal rank of the first relevant result, or zero."""
    relevant = set(relevant_ids)
    for rank, chunk_id in enumerate(retrieved_ids, start=1):
        if chunk_id in relevant:
            return 1.0 / rank
    return 0.0


def aggregate_metrics(per_query: list[dict[str, Any]]) -> MethodMetrics:
    """Macro-average Recall@1/3/5 and MRR over query-level measurements."""
    if not per_query:
        return MethodMetrics(0, 0.0, 0.0, 0.0, 0.0)
    count = len(per_query)
    return MethodMetrics(
        query_count=count,
        recall_at_1=sum(item["recall@1"] for item in per_query) / count,
        recall_at_3=sum(item["recall@3"] for item in per_query) / count,
        recall_at_5=sum(item["recall@5"] for item in per_query) / count,
        mrr=sum(item["mrr"] for item in per_query) / count,
    )


def evaluate_method(
    queries: list[QueryCase],
    method: str,
    *,
    candidate_count: int = 20,
    search_fn: Callable[..., list[SearchResult]] = search,
) -> dict[str, Any]:
    """Run one retrieval method and return overall/grouped metrics.

    ``search_fn`` is injectable so metric tests can use deterministic fixtures
    without connecting to PostgreSQL or generating embeddings.
    """
    if method not in METHODS:
        raise ValueError(f"Unknown method: {method}")
    if candidate_count < max(K_VALUES):
        raise ValueError(f"candidate_count must be at least {max(K_VALUES)} for Recall@5")
    per_query: list[dict[str, Any]] = []
    for index, case in enumerate(queries, start=1):
        logger.debug(
            "Evaluating query %d/%d: method=%s type=%s relevant_count=%d query=%r",
            index,
            len(queries),
            method,
            case.query_type,
            len(case.relevant_chunk_ids),
            case.query,
        )
        results = search_fn(case.query, mode=method, top_k=5, candidate_count=candidate_count)
        ids = [result.chunk_id for result in results]
        measurement = {
            "query": case.query,
            "type": case.query_type,
            "recall@1": recall_at_k(ids, case.relevant_chunk_ids, 1),
            "recall@3": recall_at_k(ids, case.relevant_chunk_ids, 3),
            "recall@5": recall_at_k(ids, case.relevant_chunk_ids, 5),
            "mrr": reciprocal_rank(ids, case.relevant_chunk_ids),
        }
        per_query.append(measurement)
        logger.debug(
            "Query %d/%d result: method=%s R@1=%.4f R@3=%.4f R@5=%.4f MRR=%.4f",
            index,
            len(queries),
            method,
            measurement["recall@1"],
            measurement["recall@3"],
            measurement["recall@5"],
            measurement["mrr"],
        )
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for item in per_query:
        grouped[item["type"]].append(item)
    metrics = {
        "overall": aggregate_metrics(per_query).as_dict(),
        "by_type": {query_type: aggregate_metrics(items).as_dict() for query_type, items in sorted(grouped.items())},
        "per_query": per_query,
    }
    logger.info(
        "%s evaluation complete: R@1=%.4f R@3=%.4f R@5=%.4f MRR=%.4f",
        method,
        metrics["overall"]["recall@1"],
        metrics["overall"]["recall@3"],
        metrics["overall"]["recall@5"],
        metrics["overall"]["mrr"],
    )
    return metrics


def evaluate_all(queries: list[QueryCase], candidate_count: int = 20) -> dict[str, Any]:
    """Evaluate lexical, semantic, and hybrid retrieval independently."""
    logger.info(
        "Starting evaluation: queries=%d methods=%s candidate_count=%d K=%s",
        len(queries),
        ",".join(METHODS),
        candidate_count,
        ",".join(str(value) for value in K_VALUES),
    )
    return {
        "query_count": len(queries),
        "candidate_count": candidate_count,
        "methods": {
            method: evaluate_method(queries, method, candidate_count=candidate_count)
            for method in METHODS
        },
    }


def print_report(report: dict[str, Any]) -> None:
    """Print concise overall and query-type metric tables."""
    print("Overall metrics (macro-average per query)")
    print("method   R@1      R@3      R@5      MRR")
    for method in METHODS:
        metrics = report["methods"][method]["overall"]
        print(f"{method:<8} {metrics['recall@1']:.4f}   {metrics['recall@3']:.4f}   {metrics['recall@5']:.4f}   {metrics['mrr']:.4f}")
    print("\nMetrics by query type")
    print("method   type       R@1      R@3      R@5      MRR")
    for method in METHODS:
        for query_type, metrics in report["methods"][method]["by_type"].items():
            print(f"{method:<8} {query_type:<10} {metrics['recall@1']:.4f}   {metrics['recall@3']:.4f}   {metrics['recall@5']:.4f}   {metrics['mrr']:.4f}")


def main() -> None:
    """Run evaluation against the configured PostgreSQL and local model."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--queries", type=Path, default=Path("data/golden_queries.json"))
    parser.add_argument("--candidate-count", type=int, default=20)
    parser.add_argument("--report", type=Path, default=Path("data/evaluation_report.json"))
    parser.add_argument("--log-level", choices=["DEBUG", "INFO", "WARNING", "ERROR"], default="INFO")
    args = parser.parse_args()
    logging.basicConfig(
        level=getattr(logging, args.log_level),
        stream=sys.stderr,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )
    queries = load_queries(args.queries)
    logger.info(
        "Loaded %d golden queries: path=%s candidate_count=%d report=%s",
        len(queries),
        args.queries,
        args.candidate_count,
        args.report,
    )
    report = evaluate_all(queries, args.candidate_count)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print_report(report)
    logger.info("Saved evaluation report: %s", args.report)


if __name__ == "__main__":
    main()
