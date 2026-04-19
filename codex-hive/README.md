# codex-hive

`codex-hive` is a multi-agent orchestration CLI for code tasks. It plans a mission, fans work out to role-specific agents, isolates write tasks in native Git worktrees, serializes integration, runs verification, and writes run artifacts you can inspect or resume later.

For a detailed Chinese walkthrough, see [explain.md](explain.md).

## What It Does

- Single entrypoint: `codex-hive run "<task>"`
- Native Git worktree isolation for write-enabled tasks
- Structured run state in SQLite and JSONL
- Review fan-out plus consensus scoring
- Mission drift and acceptance checks before final success
- Fake adapter for deterministic end-to-end tests
- Codex CLI adapter for `codex exec --json`

## Requirements

- Python 3.11+
- Git
- A Git repository with at least one commit before running write-heavy flows
- Optional: `codex` in `PATH` if you want `--adapter codex`

## Installation

```bash
cd /home/Creeken/Paper/codex-test/codex-hive
python3 -m pip install -e ".[dev]"
```

Verify the CLI:

```bash
codex-hive --help
```

## Quick Start

Initialize state in the current repository:

```bash
codex-hive init --repo-root .
```

Run a full fake end-to-end flow:

```bash
codex-hive run "Implement feature with tests and docs" --repo-root . --adapter fake
```

Inspect state:

```bash
codex-hive status --repo-root . --json
codex-hive inspect <run-id> --repo-root . --json
codex-hive doctor --repo-root . --json
```

Use the real Codex adapter:

```bash
codex-hive run "Refactor auth flow" --repo-root . --adapter codex
```

## Core Commands

- `init`: create `.codex-hive/` state directories and write `codex-hive.toml`
- `plan`: build the mission plan without executing workers
- `run`: execute a mission end-to-end
- `status`: list known runs from SQLite state
- `inspect`: read one run artifact bundle
- `resume`: continue a resumable run
- `cancel`: mark a run cancelled and drop a cancellation marker
- `merge`: show the merge plan for a run
- `clean`: remove `.codex-hive/`
- `doctor`: check local readiness
- `agents list`: print configured agent profiles
- `config show`: print resolved config
- `export-report`: export `run.json` to a target path
- `review`, `debate`, `judge`, `benchmark`: convenience wrappers around `run`

## Typical Run Lifecycle

1. `codex-hive init` creates:

```text
.codex-hive/
  runs/
  worktrees/
codex-hive.toml
```

2. `codex-hive run ...` does the following:

- Parse the mission into a `MissionSpec`
- Build a `PlannerOutput` with task DAG, strategy, and ownership hints
- Create a run directory under `.codex-hive/runs/<run-id>/`
- Store run/task state in `.codex-hive/state.db`
- Append lifecycle events to `.codex-hive/events.jsonl`
- Create native Git worktrees for write-enabled tasks
- Dispatch workers through the chosen adapter
- Commit worktree changes and cherry-pick them back under a serialized Git lock
- Run auto-detected verification commands
- Run Mission Keeper checks
- Write final artifacts

3. A completed run writes:

```text
.codex-hive/runs/<run-id>/
  run.json
  mission.json
  plan.json
  consensus.json
  merge-plan.json
  mission-check.json
  summary.md
  final-report.md
  events.jsonl
  tasks/
    <task-id>.json
```

Global state also lives here:

```text
.codex-hive/state.db
.codex-hive/events.jsonl
.codex-hive/worktrees/
```

## Strategies

- `plan-then-execute-council`
- `role-split-review`
- `slice-split-implementation`
- `competitive-generation`
- `debate`
- `map-reduce`

If you do not pass `--strategy`, the planner picks one heuristically from the mission text.

## Safety Model

- Write tasks run in native Git worktrees, not in-place
- Integration is serialized through a lock-backed Git operation queue
- Integration uses real Git commits plus cherry-pick, not file copy merge
- Ownership analysis can reduce parallelism when write paths overlap
- Mission Keeper can downgrade a run to `escalated` when acceptance or scope checks fail

## Configuration

Repository config lives in `codex-hive.toml`. Main knobs:

```toml
[general]
artifacts_dir = ".codex-hive/runs"
worktree_root = ".codex-hive/worktrees"
max_parallel_agents = 6
default_strategy = "auto"
default_timeout_seconds = 1800
```

See [docs/config.md](docs/config.md), [docs/architecture.md](docs/architecture.md), and [docs/recovery.md](docs/recovery.md).

## Testing

Run the full test suite:

```bash
pytest
```

The fake adapter is enough for end-to-end tests. It creates deterministic files in isolated worktrees and exercises the orchestration stack without requiring the real Codex CLI.

## Native Codex Integration

- [AGENTS.md](AGENTS.md)
- [.codex/config.toml.example](.codex/config.toml.example)
- `.codex/agents/*.toml`
- `.codex/skills/team-mode/`

## Current Boundaries

- Planning is still heuristic, not LLM-generated planning logic
- `resume` restores succeeded tasks and reruns incomplete ones, but it is not yet a full mid-command checkpoint resume for external processes
- Consensus, debate, and judge flows are usable, but still lightweight compared with a production review platform
