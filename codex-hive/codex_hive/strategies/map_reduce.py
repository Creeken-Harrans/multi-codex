"""Map reduce strategy."""

from __future__ import annotations

from .base import Strategy


class MapReduceStrategy(Strategy):
    name = "map-reduce"

    def applies(self, planner_output) -> bool:
        return all(not task.write_enabled for task in planner_output.tasks)
