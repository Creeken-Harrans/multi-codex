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
        envelope_payload = envelope.model_dump(mode="json")
        prompt = self._build_prompt(envelope_payload, cwd)
        command = [
            self.config.codex.binary,
            "exec",
            "--json",
            "--cd",
            str(cwd),
            prompt,
        ]
        trace_prefix = f"[codex-hive {assignment.run_id}/{assignment.task.task_id}/{assignment.agent_id}]"
        print(f"{trace_prefix} [WORKER] starting role={assignment.task.role}", flush=True)
        print(f"{trace_prefix} [WORKER] cwd={cwd}", flush=True)
        print(f"{trace_prefix} [WORKER] command=codex exec --json --cd {cwd} <worker prompt saved to trace>", flush=True)
        print(f"{trace_prefix} [TASK] mission={envelope.mission.mission}", flush=True)
        print(f"{trace_prefix} [TASK] {assignment.task.title} | reads={assignment.task.read_paths or ['<none>']} | writes={assignment.task.owned_paths or ['<none>']}", flush=True)
        print(f"{trace_prefix} [INPUT] summary:", flush=True)
        print(json.dumps(self._envelope_summary(envelope_payload), ensure_ascii=False, indent=2), flush=True)
        result = await run_command(
            command,
            cwd=cwd,
            timeout=self.config.general.default_timeout_seconds,
            stream_prefix=trace_prefix,
            stream_formatter=self._format_codex_stream_line,
        )
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
            "prompt": prompt,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "events": events,
            "final_message": self._extract_summary(events),
        }
        return WorkerResult.model_validate(payload)

    def _build_prompt(self, envelope_payload: dict, cwd: Path) -> str:
        budget = self._budget(envelope_payload)
        return (
            "You are a codex-hive worker.\n"
            f"Repository root for this task is exactly: {cwd}\n"
            "Treat that directory as the entire target repository, even if it looks sparse or nested.\n"
            "Do not inspect, read, search, or modify parent directories such as '..' or sibling repositories.\n"
            "Do not run commands against paths outside the repository root.\n"
            "If required files are missing, report that as part of this repository state instead of looking elsewhere.\n"
            "For write-enabled tasks, modify only assigned owned_paths.\n"
            "Work budget:\n"
            f"- Read at most {budget['max_files_read']} files unless you hit a hard blocker.\n"
            f"- Run at most {budget['max_commands']} shell commands.\n"
            f"- Inspect at most {budget['max_stdout_lines']} lines of command output.\n"
            "- Prefer the assigned read_paths and owned_paths; do not perform broad discovery unless those paths are empty.\n"
            "- If the budget is insufficient, return a blocker in WorkerResult instead of expanding the search.\n"
            "Return strict JSON matching WorkerResult. No markdown, no prose outside JSON.\n\n"
            "WorkerPromptEnvelope JSON:\n"
            f"{json.dumps(envelope_payload, ensure_ascii=False, indent=2)}"
        )

    def _format_codex_stream_line(self, label: str, text: str) -> str | None:
        if label == "stderr":
            return f"stderr: {text}"
        try:
            event = json.loads(text)
        except json.JSONDecodeError:
            return f"[CODEX] {text}"
        event_type = event.get("type")
        if event_type == "thread.started":
            return f"[CODEX] thread started: {event.get('thread_id')}"
        if event_type == "turn.started":
            return "[CODEX] turn started"
        if event_type == "turn.completed":
            usage = event.get("usage", {})
            return f"[CODEX] turn completed | input_tokens={usage.get('input_tokens')} | output_tokens={usage.get('output_tokens')}"
        if event_type == "item.completed":
            item = event.get("item", {})
            item_type = item.get("type")
            if item_type == "agent_message":
                message = item.get("text", "")
                return f"[CODEX] reply: {self._compact(message)}"
            if item_type == "command_execution":
                command = item.get("command") or item.get("cmd") or "<command>"
                status = item.get("status") or item.get("exit_code") or "completed"
                return f"[CODEX] command completed | {command} | status={status}"
            return "[CODEX] item completed:\n" + json.dumps(self._small_event(event), ensure_ascii=False, indent=2)
        if event_type:
            return "[CODEX] event:\n" + json.dumps(self._small_event(event), ensure_ascii=False, indent=2)
        return None

    def _envelope_summary(self, envelope_payload: dict) -> dict:
        assignment = envelope_payload.get("assignment", {})
        task = assignment.get("task", {})
        mission = envelope_payload.get("mission", {})
        budget = self._budget(envelope_payload)
        return {
            "run_id": assignment.get("run_id"),
            "agent_id": assignment.get("agent_id"),
            "role": task.get("role"),
            "task_id": task.get("task_id"),
            "task_title": task.get("title"),
            "task_description": task.get("description"),
            "dependencies": task.get("dependencies", []),
            "read_paths": task.get("read_paths", []),
            "owned_paths": task.get("owned_paths", []),
            "write_enabled": task.get("write_enabled"),
            "mission": mission.get("mission"),
            "acceptance_criteria": mission.get("acceptance_criteria", []),
            "budget": budget,
            "dependency_summary": envelope_payload.get("verification_summary"),
            "role_instructions": envelope_payload.get("role_instructions"),
            "output_contract": envelope_payload.get("output_contract"),
        }

    def _budget(self, envelope_payload: dict) -> dict[str, int]:
        assignment = envelope_payload.get("assignment", {})
        task = assignment.get("task", {})
        metadata = task.get("metadata") or {}
        return {
            "max_files_read": int(metadata.get("max_files_read", 8)),
            "max_commands": int(metadata.get("max_commands", 5)),
            "max_stdout_lines": int(metadata.get("max_stdout_lines", 120)),
        }

    def _small_event(self, event: dict) -> dict:
        keep = {}
        for key in ("type", "thread_id", "id", "status"):
            if key in event:
                keep[key] = event[key]
        item = event.get("item")
        if isinstance(item, dict):
            keep["item"] = {key: item.get(key) for key in ("id", "type", "status") if key in item}
        usage = event.get("usage")
        if isinstance(usage, dict):
            keep["usage"] = usage
        return keep or event

    def _compact(self, text: str, limit: int = 600) -> str:
        compacted = " ".join(text.split())
        if len(compacted) <= limit:
            return compacted
        return compacted[: limit - 3] + "..."

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
