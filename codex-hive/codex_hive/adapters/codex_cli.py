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
        events = self._parse_jsonl_events(result.stdout)
        try:
            payload = json.loads(result.stdout.strip() or "{}")
        except json.JSONDecodeError:
            payload = {
                "task_id": assignment.task.task_id,
                "agent_id": assignment.agent_id,
                "role": assignment.task.role,
                "status": WorkerStatus.succeeded.value,
                "summary": self._extract_summary(events) or result.stdout.strip() or "codex exec completed",
                "confidence": 0.5,
            }
        if "task_id" not in payload:
            payload["task_id"] = assignment.task.task_id
        if "agent_id" not in payload:
            payload["agent_id"] = assignment.agent_id
        if "role" not in payload:
            payload["role"] = assignment.task.role
        payload.setdefault("metadata", {})
        payload["metadata"]["trace"] = {
            "adapter": self.name,
            "cwd": str(cwd),
            "command": command,
            "input_envelope": envelope.model_dump(mode="json"),
            "stdout": result.stdout,
            "stderr": result.stderr,
            "events": events,
            "final_message": self._extract_summary(events),
        }
        return WorkerResult.model_validate(payload)

    def _parse_jsonl_events(self, stdout: str) -> list[dict]:
        parsed: list[dict] = []
        for line in stdout.splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                parsed.append(json.loads(line))
            except json.JSONDecodeError:
                parsed.append({"type": "raw_text", "text": line})
        return parsed

    def _extract_summary(self, events: list[dict]) -> str | None:
        for item in reversed(events):
            if item.get("type") == "item.completed":
                payload = item.get("item", {})
                if payload.get("type") == "agent_message":
                    return payload.get("text")
        return None
