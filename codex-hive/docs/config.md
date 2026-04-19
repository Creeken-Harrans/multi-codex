# Config

Main repository config file: `codex-hive.toml`

Sections:

- `general`: artifacts, worktree root, parallelism, default timeouts
- `codex`: binary path, model defaults, exec arguments
- `git`: base branch, auto-commit/push flags, serialization toggles
- `consensus`: debate/judge enablement and thresholds
- `recovery`: resume preferences and event persistence
- `verification`: auto-detection and command categories

Agent profiles are stored in `AppConfig.agents` and exposed through `codex-hive agents list`.
