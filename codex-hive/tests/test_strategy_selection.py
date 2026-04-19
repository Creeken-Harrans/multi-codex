from pathlib import Path

from codex_hive.adapters.fake_agent import FakeAgentAdapter
from codex_hive.config import AppConfig
from codex_hive.db import StateDB
from codex_hive.eventlog import EventLogger
from codex_hive.runtime.orchestrator import Orchestrator
from tests.conftest import init_git_repo


def make_orchestrator(tmp_path: Path) -> Orchestrator:
    repo = init_git_repo(tmp_path / "repo")
    config = AppConfig.default()
    return Orchestrator(
        repo,
        config,
        StateDB(repo / ".codex-hive" / "state.db"),
        EventLogger(repo / ".codex-hive" / "events.jsonl"),
        FakeAgentAdapter(),
    )


def test_auto_routes_simple_mission_to_short_flow(tmp_path: Path):
    orchestrator = make_orchestrator(tmp_path)
    plan = orchestrator.plan(orchestrator.parse_mission("Implement feature with tests and docs"))

    assert plan.strategy == "simple"
    assert [task.task_id for task in plan.tasks] == ["impl-core", "test"]
    assert all("max_files_read" in task.metadata for task in plan.tasks)
    assert "scout" not in {task.task_id for task in plan.tasks}
    assert "architect" not in {task.task_id for task in plan.tasks}


def test_explicit_council_strategy_keeps_full_flow(tmp_path: Path):
    orchestrator = make_orchestrator(tmp_path)
    plan = orchestrator.plan(orchestrator.parse_mission("Implement feature with tests and docs"), "plan-then-execute-council")

    assert plan.strategy == "plan-then-execute-council"
    assert len(plan.tasks) == 10
    assert [task.task_id for task in plan.tasks[:3]] == ["plan-review", "scout", "architect"]


def test_bug_mission_still_uses_competitive_generation(tmp_path: Path):
    orchestrator = make_orchestrator(tmp_path)
    plan = orchestrator.plan(orchestrator.parse_mission("Fix flaky bug"))

    assert plan.strategy == "competitive-generation"
    assert "impl-alt" in {task.task_id for task in plan.tasks}


def test_chinese_markdown_debate_routes_to_debate_artifact(tmp_path: Path):
    orchestrator = make_orchestrator(tmp_path)
    mission = orchestrator.parse_mission("打一场辩论赛, 辩题你自己选, 最终成果是.md文件")
    plan = orchestrator.plan(mission)

    assert plan.strategy == "debate-artifact"
    assert [task.task_id for task in plan.tasks] == ["debater-affirmative", "debater-negative", "moderator-writeup"]
    assert plan.tasks[0].write_enabled is False
    assert plan.tasks[1].write_enabled is False
    assert plan.tasks[2].owned_paths == ["debate.md"]
    assert plan.tasks[2].dependencies == ["debater-affirmative", "debater-negative"]
    assert [item.description for item in mission.acceptance_criteria] == ["documentation"]
