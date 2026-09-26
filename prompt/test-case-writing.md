---
name: test-case-writing
description: Design focused deterministic automated tests for changed behavior.
---

# Test-Case Writing

Test observable behavior with small deterministic fixtures. Cover the happy
path, empty input, one item, exact boundaries, just-below and just-above
thresholds, duplicates, malformed records, stable ordering, and interactions
such as speaker boundaries plus time limits. Avoid live databases, networks,
models, clocks, or randomness in unit tests. Use hand-calculated expected
values for ranking and metrics. Run focused tests first, then the full suite,
and report command, counts, result, and any environment blocker.
