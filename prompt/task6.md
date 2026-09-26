# Task 6 — Golden query set

Now construct the evaluation query set using the REAL transcript chunks.

Do not change retrieval implementation yet.

Inspect the actual transcript chunks and create approximately 15–30 evaluation queries.

Include:

* exact keyword queries
* paraphrases
* semantic/conceptual queries
* queries with multiple relevant chunks
* several difficult cases

Format:

{
"query": "...",
"type": "keyword|semantic|mixed",
"relevant_chunk_ids": ["..."]
}

Critical requirement:

Ground-truth relevant_chunk_ids must be determined from actual transcript content, NOT from whichever results the search system currently returns.

For each query, verify that every labeled chunk genuinely contains information relevant to the query.

Do not invent transcript content or chunk IDs.

Save as something like:

data/golden_queries.json

Also create a short summary showing:

* query count
* count by type
* number with multiple relevant chunks

Do not implement/tune retrieval based on evaluation results yet.

