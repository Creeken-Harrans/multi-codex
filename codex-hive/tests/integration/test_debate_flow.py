from pathlib import Path

from codex_hive.adapters.fake_agent import FakeAgentAdapter
from codex_hive.config import AppConfig
from codex_hive.db import StateDB
from codex_hive.eventlog import EventLogger
from codex_hive.runtime.orchestrator import Orchestrator
from tests.conftest import init_git_repo


def test_debate_flow(tmp_path: Path):
    repo = init_git_repo(tmp_path / "repo")
    config = AppConfig.default()
    db = StateDB(repo / ".codex-hive" / "state.db")
    eventlog = EventLogger(repo / ".codex-hive" / "events.jsonl")
    orchestrator = Orchestrator(repo, config, db, eventlog, FakeAgentAdapter())
    planner_output = orchestrator.plan(orchestrator.parse_mission("Fix flaky bug"), "competitive-generation")
    report = __import__("asyncio").run(orchestrator.execute_plan("run2", planner_output))
    assert report.consensus_report is not None
    assert report.consensus_report.debate_rounds >= 1
