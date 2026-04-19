# codex-hive

**A production-ready multi-Codex orchestration system with worktree isolation, structured consensus, debate, competitive generation, and merge-safe execution.**

`codex-hive` is a hybrid system:

- Native Codex collaboration layer: `AGENTS.md`, `.codex/agents/*.toml`, skills, and `codex exec` compatibility.
- External orchestration layer: Python CLI/runtime, task DAG execution, worktree isolation, SQLite state, JSONL events, consensus scoring, merge planning, and recovery.

The system is built so one top-level Codex, or a human at the terminal, can issue a single command such as:

```bash
codex-hive run "Implement OAuth login with tests and docs"
```

The runtime then handles mission parsing, planning, role routing, parallel agent execution, structured review, mission drift detection, artifacts, and resumable run state.

## Why Hybrid

Native subagents are strong for bounded, read-heavy, short-lived tasks. They are weaker for long write-heavy pipelines where branch/worktree safety, crash recovery, and merge serialization matter. `codex-hive` keeps both:

- Use Codex-native agents for local repo exploration and lightweight delegation.
- Use `codex-hive` worktree orchestration for large parallel implementation, competitive generation, debate, and merge-safe execution.

## Features

- CLI commands: `init`, `run`, `plan`, `status`, `inspect`, `resume`, `cancel`, `merge`, `clean`, `doctor`, `agents list`, `config show`, `export-report`, plus `review`, `debate`, `judge`, `benchmark`.
- Task DAG execution with statuses: `pending`, `ready`, `blocked`, `running`, `retrying`, `awaiting-approval`, `awaiting-merge`, `succeeded`, `failed`, `cancelled`, `escalated`.
- Strategies: map-reduce, role-split review, slice-split implementation, competitive generation, debate, and plan-then-execute council.
- Structured schemas with Pydantic v2.
- Consensus engine with agreement ratio, evidence weighting, reliability weighting, and verification levels.
- Mission Keeper with scope drift and acceptance coverage checks.
- Worktree manager and serialized git op queue.
- Fake adapter for testable orchestration without Codex installed.
- Codex CLI adapter for `codex exec`.
- SQLite run/task/execution state plus JSONL event log.
- Human-readable and machine-readable artifacts.

## Installation

```bash
cd /home/Creeken/Paper/codex-test/codex-hive
/home/Creeken/miniconda3/envs/pytorch/bin/python -m pip install -e .[dev]
```

## Quick Start

```bash
codex-hive init
codex-hive run "Build a feature end-to-end" --adapter fake
codex-hive status
codex-hive inspect <run-id>
```

To use the real Codex CLI adapter:

```bash
codex-hive run "Refactor auth flow" --adapter codex
```

## Common Workflows

### Large implementation

```bash
codex-hive run "Implement OAuth login with tests and docs"
```

This uses mission parsing, plan-then-execute, isolated worktrees for write-heavy tasks, review fan-out, consensus, merge planning, verification, and a final mission fidelity check.

### Competitive bug fixing

```bash
codex-hive run "Fix this flaky test in CI" --strategy competitive-generation
```

This creates competing implementers, judges their outcomes, and merges the strongest candidate into the integration step.

### Strict review

```bash
codex-hive review "Review current branch for correctness, security, performance, and maintainability"
```

This triggers parallel reviewers, finding deduplication, consensus scoring, and optional debate escalation.

## Configuration

Repository config lives in `codex-hive.toml`. Example defaults:

```toml
[general]
artifacts_dir = ".codex-hive/runs"
worktree_root = ".codex-hive/worktrees"
max_parallel_agents = 6
default_strategy = "auto"
default_timeout_seconds = 1800
```

See [docs/config.md](docs/config.md) for the full surface.

## Artifacts

Each run writes:

```text
.codex-hive/runs/<run-id>/
  run.json
  summary.md
  mission.json
  consensus.json
  merge-plan.json
  mission-check.json
  final-report.md
  tasks/
```

The state database is `.codex-hive/state.db` and the event stream is `.codex-hive/events.jsonl`.

## Recovery

- `codex-hive resume <run-id>` replays the mission with stored run metadata.
- Worktrees live under `.codex-hive/worktrees/`.
- `codex-hive clean` removes the local state directory.
- `codex-hive doctor` checks key dependencies and local state readiness.

See [docs/recovery.md](docs/recovery.md).

## Safety

- Write-heavy tasks use isolated worktrees.
- High-risk git operations are serialized via a lock-backed git op queue.
- Ownership analysis detects overlapping write paths and degrades parallelism.
- Mission Keeper blocks completion if scope drift or acceptance gaps are detected.
- Reviewers are separated from implementers through structured worker envelopes.

See [docs/safety.md](docs/safety.md).

## Testing

```bash
make test
```

The fake adapter powers end-to-end integration tests without requiring Codex. If you have `codex` installed, you can manually run smoke tests against the real adapter.

## Native Codex Integration

- [AGENTS.md](AGENTS.md) defines repository-level operating instructions.
- `.codex/config.toml.example` shows how to expose these agents to Codex.
- `.codex/agents/*.toml` define role-specific personas.
- `.codex/skills/team-mode/` teaches a top-level Codex when to route tasks through `codex-hive`.

## Current v1 Boundaries

- Worktree creation is filesystem-copy-based for portability in tests; Git-native worktree plumbing can be layered in later.
- Merge integration is safe file copy from isolated worktrees rather than full branch merge logic.
- Real `codex exec` output normalization is intentionally simple and expects JSON-friendly output when possible.
