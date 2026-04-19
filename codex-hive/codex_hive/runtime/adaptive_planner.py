"""Lightweight Codex-backed task planning."""

from __future__ import annotations

import json
from pathlib import Path

from ..config import AppConfig
from ..git.ownership import analyze_ownership
from ..models import MissionSpec, PlannerOutput, TaskSpec, TaskType
from ..utils.subprocesses import run_command


def should_use_adaptive_planner(mission: MissionSpec) -> bool:
    lowered = mission.mission.lower()
    return any(marker in lowered for marker in ("辩论", "debate", "协作", "collaborat", "角色", "worker", "agent"))


async def plan_with_codex(repo_root: Path, config: AppConfig, mission: MissionSpec) -> PlannerOutput | None:
    prompt = _planning_prompt(mission)
    command = [config.codex.binary, "exec", "--json", "--cd", str(repo_root), prompt]
    print("[ADAPTIVE_PLAN] asking Codex to choose worker roles; repo reads are forbidden", flush=True)
    result = await run_command(command, cwd=repo_root, timeout=min(config.general.default_timeout_seconds, 120), stream_prefix="[ADAPTIVE_PLAN]", stream_formatter=_format_plan_stream)
    if result.returncode != 0:
        print(f"[ADAPTIVE_PLAN] failed; falling back to built-in planner: {result.stderr or result.stdout}", flush=True)
        return None
    message = _extract_final_message(result.stdout)
    if message is None:
        print("[ADAPTIVE_PLAN] no final JSON message; falling back to built-in planner", flush=True)
        return None
    try:
        payload = json.loads(message)
    except json.JSONDecodeError:
        print("[ADAPTIVE_PLAN] final message was not JSON; falling back to built-in planner", flush=True)
        return None
    try:
        tasks = [_task_from_payload(item) for item in payload.get("tasks", [])]
    except (TypeError, ValueError):
        print("[ADAPTIVE_PLAN] invalid task schema; falling back to built-in planner", flush=True)
        return None
    if not tasks:
        print("[ADAPTIVE_PLAN] empty task list; falling back to built-in planner", flush=True)
        return None
    strategy = str(payload.get("strategy") or "adaptive-codex")
    notes = payload.get("notes") if isinstance(payload.get("notes"), list) else []
    return PlannerOutput(mission=mission, tasks=tasks, strategy=strategy, ownership=analyze_ownership(tasks), notes=["codex adaptive planner", *[str(item) for item in notes]])


def _planning_prompt(mission: MissionSpec) -> str:
    return (
        "You are the codex-hive adaptive planner. Decide how many workers are needed and what each worker should do.\n"
        "Hard rules:\n"
        "- Do not inspect files. Do not run shell commands. Use only the mission text below.\n"
        "- Use 1 to 5 workers.\n"
        "- For a debate mission, use at least 3 workers: two opposing debaters and one moderator/host.\n"
        "- Exactly one final writer/moderator should write the requested artifact when the mission asks for a file.\n"
        "- Read-only workers must have write_enabled=false and no owned_paths.\n"
        "- Keep dependencies minimal; independent debaters should run in parallel.\n"
        "- Return JSON only, no markdown.\n\n"
        "Required JSON schema:\n"
        "{\n"
        '  "strategy": "adaptive-codex",\n'
        '  "tasks": [\n'
        "    {\n"
        '      "task_id": "short-kebab-id",\n'
        '      "title": "human title",\n'
        '      "description": "specific assignment",\n'
        '      "role": "short_role_name",\n'
        '      "dependencies": [],\n'
        '      "read_paths": [],\n'
        '      "owned_paths": [],\n'
        '      "write_enabled": false,\n'
        '      "role_instructions": "worker-specific instructions"\n'
        "    }\n"
        "  ],\n"
        '  "notes": []\n'
        "}\n\n"
        f"Mission: {mission.mission}\n"
    )


def _task_from_payload(payload: dict) -> TaskSpec:
    task_id = str(payload["task_id"])
    role = str(payload.get("role") or task_id.replace("-", "_"))
    write_enabled = bool(payload.get("write_enabled", False))
    owned_paths = [str(item) for item in payload.get("owned_paths", [])]
    metadata = {
        "confidence": 0.82,
        "strategy": "adaptive-codex",
        "max_files_read": int(payload.get("max_files_read", 0)),
        "max_commands": int(payload.get("max_commands", 2 if write_enabled else 1)),
        "max_stdout_lines": int(payload.get("max_stdout_lines", 80 if write_enabled else 40)),
    }
    if payload.get("role_instructions"):
        metadata["role_instructions"] = str(payload["role_instructions"])
    return TaskSpec(
        task_id=task_id,
        title=str(payload.get("title") or task_id),
        description=str(payload.get("description") or task_id),
        type=TaskType.documentation if write_enabled or owned_paths else TaskType.exploration,
        role=role,
        dependencies=[str(item) for item in payload.get("dependencies", [])],
        read_paths=[str(item) for item in payload.get("read_paths", [])],
        owned_paths=owned_paths,
        write_enabled=write_enabled,
        metadata=metadata,
    )


def _extract_final_message(stdout: str) -> str | None:
    for line in reversed(stdout.splitlines()):
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        if event.get("type") != "item.completed":
            continue
        item = event.get("item", {})
        if isinstance(item, dict) and item.get("type") == "agent_message":
            return item.get("text")
    return None


def _format_plan_stream(label: str, text: str) -> str | None:
    if label == "stderr":
        return f"stderr: {text}"
    try:
        event = json.loads(text)
    except json.JSONDecodeError:
        return text
    event_type = event.get("type")
    if event_type == "thread.started":
        return f"thread started: {event.get('thread_id')}"
    if event_type == "turn.started":
        return "turn started"
    if event_type == "turn.completed":
        usage = event.get("usage", {})
        return f"turn completed | input_tokens={usage.get('input_tokens')} | output_tokens={usage.get('output_tokens')}"
    if event_type == "item.completed":
        item = event.get("item", {})
        if item.get("type") == "agent_message":
            return "planner reply received"
        if item.get("type") == "command_execution":
            return f"unexpected command completed: {item.get('command') or item.get('cmd')}"
    return None
