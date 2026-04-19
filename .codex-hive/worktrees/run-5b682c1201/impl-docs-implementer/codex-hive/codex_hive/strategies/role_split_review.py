"""Role split review strategy."""

from __future__ import annotations

from .base import Strategy


class RoleSplitReviewStrategy(Strategy):
    name = "role-split-review"

    def applies(self, planner_output) -> bool:
        return any(task.role.endswith("reviewer") or task.role == "reviewer" for task in planner_output.tasks)
