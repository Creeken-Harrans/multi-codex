"""Slice split implementation strategy."""

from __future__ import annotations

from .base import Strategy


class SliceSplitImplementationStrategy(Strategy):
    name = "slice-split-implementation"

    def applies(self, planner_output) -> bool:
        writable = [task for task in planner_output.tasks if task.write_enabled]
        return len(writable) > 1
