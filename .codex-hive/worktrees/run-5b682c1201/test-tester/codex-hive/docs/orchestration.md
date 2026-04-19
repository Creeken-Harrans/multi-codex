# Orchestration

The main run flow is:

1. Parse mission into `MissionSpec`.
2. Build `PlannerOutput` with tasks, risk, ownership analysis, and selected strategy.
3. Dispatch ready tasks in dependency order.
4. Create isolated worktrees for write-enabled tasks.
5. Persist state into SQLite and append events to JSONL.
6. Aggregate findings into consensus and optional debate/judge adjustment.
7. Produce a merge plan and integrate accepted changes.
8. Run verification commands detected in the repo.
9. Run mission drift/fidelity checks.
10. Persist artifacts and final reports.

This v1 planner is heuristic-driven but fully executable and testable.
