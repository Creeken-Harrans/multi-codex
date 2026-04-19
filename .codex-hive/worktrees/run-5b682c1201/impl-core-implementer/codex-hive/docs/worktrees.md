# Worktrees

Write-enabled tasks receive isolated directories under:

```text
.codex-hive/worktrees/<run-id>/<task-id>-<role>/
```

The v1 implementation uses repo-copy isolation to keep local testing simple and deterministic. Each write task gets:

- a unique worktree path
- a synthetic branch name
- lifecycle cleanup commands through `codex-hive clean`

Ownership analysis marks overlapping write paths and can force serialization.
