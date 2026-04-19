"""Debate strategy."""

from __future__ import annotations

from .base import Strategy


class DebateStrategy(Strategy):
    name = "debate"

    def applies(self, planner_output) -> bool:
        return planner_output.strategy == self.name
