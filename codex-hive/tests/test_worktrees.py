from pathlib import Path

from codex_hive.git.worktrees import WorktreeManager
from tests.conftest import init_git_repo


def test_worktree_lifecycle(tmp_path: Path):
    repo = init_git_repo(tmp_path / "repo")
    manager = WorktreeManager(repo, tmp_path / "worktrees")
    path, branch = manager.create("run1", "task1", "implementer")
    assert Path(path).exists()
    assert (Path(path) / ".git").exists()
    assert branch.startswith("codex-hive/run1")
    manager.clean_run("run1")
    assert not (tmp_path / "worktrees" / "run1").exists()
