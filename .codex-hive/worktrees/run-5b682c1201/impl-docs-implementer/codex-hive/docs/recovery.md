# Recovery

Recovery primitives:

- SQLite stores run, task, and execution state
- JSONL stores append-only event logs
- artifacts persist worker outputs and reports
- `codex-hive resume <run-id>` reuses the stored mission and strategy

For stale local state:

- inspect `.codex-hive/events.jsonl`
- inspect `.codex-hive/runs/<run-id>/`
- run `codex-hive clean` if you need to reset local orchestration state
