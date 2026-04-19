import asyncio
from pathlib import Path

from codex_hive.adapters.fake_agent import FakeAgentAdapter
from codex_hive.models import MissionSpec, TaskAssignment, TaskSpec, TaskType, WorkerPromptEnvelope


def test_fake_agent_creates_files(tmp_path: Path):
    adapter = FakeAgentAdapter()
    task = TaskSpec(task_id="impl", title="impl", description="impl", type=TaskType.implementation, role="implementer", owned_paths=["x.py"], write_enabled=True)
    assignment = TaskAssignment(run_id="r1", task=task, agent_id="a1", worktree_path=str(tmp_path), branch_name="branch")
    envelope = WorkerPromptEnvelope(assignment=assignment, mission=MissionSpec(mission="m"), role_instructions="do it")
    result = asyncio.run(adapter.run_assignment(assignment, envelope, Path(tmp_path)))
    assert (tmp_path / "x.py").exists()
    assert result.files_changed == ["x.py"]
