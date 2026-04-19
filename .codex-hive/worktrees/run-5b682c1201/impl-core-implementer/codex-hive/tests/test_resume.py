from pathlib import Path

from codex_hive.db import StateDB
from codex_hive.models import RunRecord, RunStatus
from codex_hive.runtime.resume import ResumeManager


def test_resume_lists_failed_runs(tmp_path: Path):
    db = StateDB(tmp_path / "state.db")
    db.upsert_run(RunRecord(run_id="r1", mission="m", strategy="auto", status=RunStatus.failed, repo_root=".", artifacts_dir="."))
    resumable = ResumeManager(db).resumable_runs()
    assert resumable[0].run_id == "r1"
