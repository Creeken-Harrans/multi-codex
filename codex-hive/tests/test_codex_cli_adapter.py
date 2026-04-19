from pathlib import Path

from codex_hive.adapters.codex_cli import CodexCLIAdapter
from codex_hive.config import AppConfig
from codex_hive.models import MissionSpec, TaskAssignment, TaskSpec, TaskType, WorkerPromptEnvelope


def test_codex_prompt_constrains_worker_to_cwd(tmp_path: Path, monkeypatch):
    monkeypatch.setattr("shutil.which", lambda binary: "/usr/bin/codex")
    adapter = CodexCLIAdapter(AppConfig.default())
    task = TaskSpec(
        task_id="scout",
        title="Scout",
        description="Scout",
        type=TaskType.exploration,
        role="scout",
        read_paths=["."],
        metadata={"max_files_read": 3, "max_commands": 2, "max_stdout_lines": 40},
    )
    assignment = TaskAssignment(run_id="r1", task=task, agent_id="a1")
    envelope = WorkerPromptEnvelope(assignment=assignment, mission=MissionSpec(mission="m"), role_instructions="read only")
    prompt = adapter._build_prompt(envelope.model_dump(mode="json"), tmp_path)
    assert f"Repository root for this task is exactly: {tmp_path}" in prompt
    assert "Do not inspect, read, search, or modify parent directories" in prompt
    assert "Read at most 3 files" in prompt
    assert "Run at most 2 shell commands" in prompt
    assert "Inspect at most 40 lines of command output" in prompt
    assert "WorkerPromptEnvelope JSON" in prompt
