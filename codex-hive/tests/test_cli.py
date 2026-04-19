from typer.testing import CliRunner

from codex_hive.cli import app
from tests.conftest import init_git_repo


runner = CliRunner()


def test_init_and_doctor(tmp_path):
    result = runner.invoke(app, ["init", "--repo-root", str(tmp_path)])
    assert result.exit_code == 0
    result = runner.invoke(app, ["doctor", "--repo-root", str(tmp_path), "--json"])
    assert result.exit_code == 0
    assert "repo_root" in result.stdout


def test_cancel_writes_marker(tmp_path):
    repo = init_git_repo(tmp_path / "repo")
    assert runner.invoke(app, ["init", "--repo-root", str(repo)]).exit_code == 0
    run_result = runner.invoke(app, ["run", "Implement feature with tests and docs", "--repo-root", str(repo), "--adapter", "fake"])
    assert run_result.exit_code == 0
    status_result = runner.invoke(app, ["status", "--repo-root", str(repo), "--json"])
    assert status_result.exit_code == 0
    run_id = status_result.stdout.split('"run_id": "')[1].split('"')[0]
    cancel_result = runner.invoke(app, ["cancel", run_id, "--repo-root", str(repo)])
    assert cancel_result.exit_code == 0
    assert (repo / ".codex-hive" / "runs" / run_id / "cancelled").exists()
