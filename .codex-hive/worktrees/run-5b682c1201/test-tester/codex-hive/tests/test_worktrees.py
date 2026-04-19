from pathlib import Path

from codex_hive.git.worktrees import WorktreeManager


def test_worktree_lifecycle(tmp_path: Path):
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "file.txt").write_text("x", encoding="utf-8")
    manager = WorktreeManager(repo, tmp_path / "worktrees")
    path, branch = manager.create("run1", "task1", "implementer")
    assert Path(path).exists()
    assert branch.startswith("codex-hive/run1")
    manager.clean_run("run1")
    assert not (tmp_path / "worktrees" / "run1").exists()
