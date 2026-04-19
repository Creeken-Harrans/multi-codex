# Architecture

`codex-hive` uses a layered design:

- CLI layer: Typer + Rich commands for runs, planning, state inspection, and recovery.
- Runtime layer: mission parsing, planning heuristics, task scheduling, dispatch, state machine, and orchestration.
- Adapter layer: real `codex exec` integration plus a deterministic fake adapter for tests.
- Safety layer: worktree manager, ownership conflict analysis, serialized git operation queue, mission guard, and verification runner.
- Result layer: consensus engine, merge plan, artifacts, SQLite state, and JSONL event stream.

The orchestrator is intentionally not the main implementer. It coordinates role-specific worker tasks and keeps reviewer inputs isolated through structured prompt envelopes.
