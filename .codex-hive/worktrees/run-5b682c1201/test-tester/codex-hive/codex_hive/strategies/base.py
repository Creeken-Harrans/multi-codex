"""Strategy abstraction."""

from __future__ import annotations

from dataclasses import dataclass

from ..models import PlannerOutput


@dataclass(slots=True)
class StrategyChoice:
    name: str
    reason: str


class Strategy:
    name = "base"

    def applies(self, planner_output: PlannerOutput) -> bool:
        raise NotImplementedError
