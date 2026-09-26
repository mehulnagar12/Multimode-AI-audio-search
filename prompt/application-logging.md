---
name: application-logging
description: Add or improve structured, visible application logging for CLI and service workflows without changing business behavior.
---

# Application Logging

Use standard logging rather than ad-hoc prints. Configure logging at CLI entry
points. Keep stdout usable for command output and send lifecycle logs to
stderr. INFO should show startup, configuration, progress, counts, outputs,
and completion; DEBUG may show per-record decisions and diagnostics. Use
WARNING for recoverable anomalies and ERROR with context for failures. Make
log levels configurable, keep secrets out of logs, and validate normal and
DEBUG runs without changing results.
