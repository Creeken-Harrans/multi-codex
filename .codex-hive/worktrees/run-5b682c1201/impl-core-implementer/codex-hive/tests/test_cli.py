from typer.testing import CliRunner

from codex_hive.cli import app


runner = CliRunner()


def test_init_and_doctor(tmp_path):
    result = runner.invoke(app, ["init", "--repo-root", str(tmp_path)])
    assert result.exit_code == 0
    result = runner.invoke(app, ["doctor", "--repo-root", str(tmp_path), "--json"])
    assert result.exit_code == 0
    assert "repo_root" in result.stdout
