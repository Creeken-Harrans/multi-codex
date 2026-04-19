"""Agent adapter base."""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path

from ..models import TaskAssignment, WorkerPromptEnvelope, WorkerResult


class AgentAdapter(ABC):
    name = "base"

    @abstractmethod
    async def run_assignment(self, assignment: TaskAssignment, envelope: WorkerPromptEnvelope, cwd: Path) -> WorkerResult:
        raise NotImplementedError
