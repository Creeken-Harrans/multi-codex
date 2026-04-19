# AGENTS.md

## Project Purpose

`codex-hive` is a multi-Codex orchestration system. Prefer `codex-hive run` for complex, multi-stage, high-risk, cross-directory, or review-heavy work.

## Core Commands

- `codex-hive init`
- `codex-hive plan "<task>"`
- `codex-hive run "<task>" --adapter fake`
- `codex-hive run "<task>" --adapter codex`
- `codex-hive status`
- `codex-hive inspect <run-id>`
- `codex-hive resume <run-id>`
- `codex-hive export-report <run-id>`
- `make test`

## Engineering Rules

- Use Python 3.11+.
- Keep types explicit.
- Add tests for orchestration, state, consensus, mission guard, and worktree behavior.
- Do not bypass `.codex-hive` artifacts or direct-write shared branches for write-heavy work.
- Do not bypass the central git op queue for merge-like operations.
- Keep reviewer roles read-only and finding-focused.

## Modification Constraints

- Write-heavy tasks should execute in isolated worktrees under `.codex-hive/worktrees/`.
- Artifacts live under `.codex-hive/runs/`.
- State is persisted in `.codex-hive/state.db`.
- Event logs are persisted in `.codex-hive/events.jsonl`.

## Workflow Guidance

- For large tasks: run `codex-hive plan`, then `codex-hive run`.
- For strict review: use `codex-hive review`.
- For flaky bug fixing or competing ideas: use `codex-hive run ... --strategy competitive-generation`.
- Reviewers should enumerate findings with evidence and severity, not general praise.
