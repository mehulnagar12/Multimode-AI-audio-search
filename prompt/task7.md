# Task 7 — Automated retrieval evaluation

Implement automated retrieval evaluation using the golden query set.

Evaluate independently:

* lexical
* semantic
* hybrid

Required metric:

Recall@K =
number of relevant chunks retrieved in top K
/
total relevant chunks for that query

Calculate:

* Recall@1
* Recall@3
* Recall@5

Report:

1. overall Recall@K
2. Recall@K grouped by query type
3. results for lexical vs semantic vs hybrid

Example:

method       R@1   R@3   R@5
lexical
semantic
hybrid

Add MRR only if implementation remains simple.

Add deterministic tests that verify metric calculations using known fixtures.

Do not fabricate results.

Run evaluation against the actual dataset and report the measured numbers.

If hybrid underperforms either individual retriever, investigate and explain the cause rather than hiding it.

Do not aggressively tune against the small golden set; avoid overfitting.
