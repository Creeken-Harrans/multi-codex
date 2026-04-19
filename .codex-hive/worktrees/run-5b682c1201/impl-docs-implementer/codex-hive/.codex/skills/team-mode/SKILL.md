# team-mode

Use this skill when:

- the task spans multiple modules or directories
- the task needs independent reviewers
- the task benefits from competing implementations
- the task is long-running or needs resume/recovery
- the task is write-heavy and should use isolated worktrees

## Default Action

Run:

```bash
python .codex/skills/team-mode/scripts/launch_team.py "<task>"
```

## Rules

- Prefer `codex-hive run` over ad hoc manual multi-agent coordination.
- Keep reviewer tasks independent from implementer inner context.
- Do not merge directly when `codex-hive` artifacts indicate unresolved mission drift or consensus issues.
