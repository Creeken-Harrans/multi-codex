"""Codex CLI adapter."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

from ..config import AppConfig
from ..errors import ConfigurationError, RetryableAgentError
from ..models import TaskAssignment, WorkerPromptEnvelope, WorkerResult, WorkerStatus
from ..utils.subprocesses import run_command
from .base import AgentAdapter


class CodexCLIAdapter(AgentAdapter):
    name = "codex-cli"

    def __init__(self, config: AppConfig) -> None:
        self.config = config
        if shutil.which(config.codex.binary) is None:
            raise ConfigurationError(f"Codex binary not found: {config.codex.binary}")

    async def run_assignment(self, assignment: TaskAssignment, envelope: WorkerPromptEnvelope, cwd: Path) -> WorkerResult:
        command = [
            self.config.codex.binary,
            "exec",
            "--json",
            json.dumps(envelope.model_dump(mode="json")),
        ]
        result = await run_command(command, cwd=cwd, timeout=self.config.general.default_timeout_seconds)
        if result.returncode != 0:
            raise RetryableAgentError(result.stderr or result.stdout)
        try:
            payload = json.loads(result.stdout.strip() or "{}")
        except json.JSONDecodeError:
            payload = {
                "task_id": assignment.task.task_id,
                "agent_id": assignment.agent_id,
                "role": assignment.task.role,
                "status": WorkerStatus.succeeded.value,
                "summary": result.stdout.strip() or "codex exec completed",
                "confidence": 0.5,
            }
        if "task_id" not in payload:
            payload["task_id"] = assignment.task.task_id
        if "agent_id" not in payload:
            payload["agent_id"] = assignment.agent_id
        if "role" not in payload:
            payload["role"] = assignment.task.role
        return WorkerResult.model_validate(payload)
