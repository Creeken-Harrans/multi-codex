from pathlib import Path

from typer.testing import CliRunner

from codex_hive.cli import app


runner = CliRunner()


def test_end_to_end_fake(tmp_path: Path):
    assert runner.invoke(app, ["init", "--repo-root", str(tmp_path)]).exit_code == 0
    result = runner.invoke(app, ["run", "Implement feature with tests and docs", "--repo-root", str(tmp_path), "--adapter", "fake"])
    assert result.exit_code == 0
    status = runner.invoke(app, ["status", "--repo-root", str(tmp_path)])
    assert status.exit_code == 0
    assert "run-" in status.stdout
