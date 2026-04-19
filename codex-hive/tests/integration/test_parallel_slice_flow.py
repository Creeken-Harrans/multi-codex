from pathlib import Path

from codex_hive.adapters.fake_agent import FakeAgentAdapter
from codex_hive.config import AppConfig
from codex_hive.db import StateDB
from codex_hive.eventlog import EventLogger
from codex_hive.runtime.orchestrator import Orchestrator


def test_parallel_slice_flow(tmp_path: Path):
    config = AppConfig.default()
    db = StateDB(tmp_path / ".codex-hive" / "state.db")
    eventlog = EventLogger(tmp_path / ".codex-hive" / "events.jsonl")
    orchestrator = Orchestrator(tmp_path, config, db, eventlog, FakeAgentAdapter())
    planner_output = orchestrator.plan(orchestrator.parse_mission("Implement feature"))
    report = __import__("asyncio").run(orchestrator.execute_plan("run1", planner_output))
    assert report.worker_results
    assert (tmp_path / ".codex-hive" / "runs" / "run1" / "run.json").exists()
