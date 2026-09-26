# Coding Agent Disclosure

This project was developed with coding-agent assistance (CODEX). The agent was
directed incrementally using the task prompts and skill instructions archived
in the `prompt/` folder.

## Prompt archive

- [Task 1 — dataset inspection](prompt/task1.md)
- [Task 2 — transcription and speaker alignment](prompt/task2.md)
- [Task 3 — searchable chunking](prompt/task3.md)
- [Task 4 — PostgreSQL and pgvector ingestion](prompt/task4.md)
- [Task 5 — retrieval and RRF](prompt/task5.md)
- [Task 6 — golden query set](prompt/task6.md)
- [Task 7 — automated evaluation](prompt/task7.md)

## Skills used

- [Application logging](prompt/application-logging.md)
- [Test-case writing](prompt/test-case-writing.md)

## Direction and decisions

- The work was split into task-level prompts to reduce context size while
  preserving the end-to-end architecture.
- Real dataset inspection was required before implementation; metadata and
  transcript chunks were not to be fabricated.
- CALLHOME speaker intervals were used as ground truth, with deterministic
  overlap-based alignment and speaker-aware chunking.
- Retrieval and evaluation were kept separate, with exact vector search as the
  baseline and RRF used for hybrid ranking.
- Logging and tests were added using the archived skill guidance, emphasizing
  visible lifecycle progress, deterministic fixtures, boundary cases, and
  measurable results.
