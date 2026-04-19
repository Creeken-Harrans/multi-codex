"""Worker dispatching."""

from __future__ import annotations

from pathlib import Path

from ..adapters.base import AgentAdapter
from ..models import TaskAssignment, WorkerPromptEnvelope, WorkerResult


class Dispatcher:
    def __init__(self, adapter: AgentAdapter) -> None:
        self.adapter = adapter

    async def dispatch(self, assignment: TaskAssignment, envelope: WorkerPromptEnvelope, cwd: Path) -> WorkerResult:
        return await self.adapter.run_assignment(assignment, envelope, cwd)
