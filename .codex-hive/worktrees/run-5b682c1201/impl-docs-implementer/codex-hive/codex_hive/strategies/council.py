"""Plan then execute council strategy."""

from __future__ import annotations

from .base import Strategy


class CouncilStrategy(Strategy):
    name = "plan-then-execute-council"

    def applies(self, planner_output) -> bool:
        return planner_output.strategy == self.name
