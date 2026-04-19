from pathlib import Path

from codex_hive.adapters.fake_agent import FakeAgentAdapter
from codex_hive.config import AppConfig
from codex_hive.db import StateDB
from codex_hive.eventlog import EventLogger
from codex_hive.models import RunRecord, RunStatus, StoredTaskRecord, WorkerResult, WorkerStatus
from codex_hive.runtime.orchestrator import Orchestrator
from codex_hive.runtime.resume import ResumeManager
from tests.conftest import init_git_repo


def test_resume_lists_failed_runs(tmp_path: Path):
    db = StateDB(tmp_path / "state.db")
    db.upsert_run(RunRecord(run_id="r1", mission="m", strategy="auto", status=RunStatus.failed, repo_root=".", artifacts_dir="."))
    resumable = ResumeManager(db).resumable_runs()
    assert resumable[0].run_id == "r1"


def test_resume_keeps_succeeded_tasks(tmp_path: Path):
    repo = init_git_repo(tmp_path / "repo")
    db = StateDB(repo / ".codex-hive" / "state.db")
    eventlog = EventLogger(repo / ".codex-hive" / "events.jsonl")
    orchestrator = Orchestrator(repo, AppConfig.default(), db, eventlog, FakeAgentAdapter())
    result = WorkerResult(
        task_id="plan",
        agent_id="planner-1",
        role="planner",
        status=WorkerStatus.succeeded,
        summary="planned",
    )
    db.upsert_run(RunRecord(run_id="run-1", mission="Implement feature with tests and docs", strategy="plan-then-execute-council", status=RunStatus.failed, repo_root=str(repo), artifacts_dir=str(repo / ".codex-hive" / "runs" / "run-1")))
    db.upsert_task(StoredTaskRecord(run_id="run-1", task_id="plan", role="planner", status=RunStatus.succeeded, payload=result.model_dump(mode="json")))
    db.upsert_task(StoredTaskRecord(run_id="run-1", task_id="impl-core", role="implementer", status=RunStatus.failed, payload={"error": "boom"}))
    statuses, results = orchestrator._load_resume_state("run-1")
    assert statuses["plan"] == RunStatus.succeeded
    assert statuses["impl-core"] == RunStatus.pending
    assert len(results) == 1
    assert results[0].task_id == "plan"
