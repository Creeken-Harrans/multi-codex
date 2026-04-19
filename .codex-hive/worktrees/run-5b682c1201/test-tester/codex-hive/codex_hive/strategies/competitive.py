"""Competitive generation strategy."""

from __future__ import annotations

from .base import Strategy


class CompetitiveGenerationStrategy(Strategy):
    name = "competitive-generation"

    def applies(self, planner_output) -> bool:
        return planner_output.strategy == self.name
