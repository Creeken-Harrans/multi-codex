from pathlib import Path

from typer.testing import CliRunner

from codex_hive.cli import app
from tests.conftest import init_git_repo


runner = CliRunner()


def test_end_to_end_fake(tmp_path: Path):
    repo = init_git_repo(tmp_path / "repo")
    assert runner.invoke(app, ["init", "--repo-root", str(repo)]).exit_code == 0
    result = runner.invoke(app, ["run", "Implement feature with tests and docs", "--repo-root", str(repo), "--adapter", "fake"])
    assert result.exit_code == 0
    status = runner.invoke(app, ["status", "--repo-root", str(repo)])
    assert status.exit_code == 0
    assert "run-" in status.stdout
    runs_dir = repo / ".codex-hive" / "runs"
    run_dirs = [item for item in runs_dir.iterdir() if item.is_dir()]
    assert len(run_dirs) == 1
    run_dir = run_dirs[0]
    assert (run_dir / "plan.json").exists()
    assert (run_dir / "events.jsonl").exists()
