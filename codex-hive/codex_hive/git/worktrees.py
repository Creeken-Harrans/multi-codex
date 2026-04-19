"""Git worktree management."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

from ..errors import ConfigurationError
from ..utils.paths import ensure_dir


class WorktreeManager:
    def __init__(self, repo_root: Path, worktree_root: Path) -> None:
        self.repo_root = repo_root.resolve()
        self.worktree_root = ensure_dir(worktree_root.resolve())

    def worktree_path(self, run_id: str, task_id: str, role: str) -> Path:
        return self.worktree_root / run_id / f"{task_id}-{role}"

    def branch_name(self, run_id: str, task_id: str, role: str) -> str:
        return f"codex-hive/{run_id}/{task_id}/{role}"

    def create(self, run_id: str, task_id: str, role: str) -> tuple[str, str]:
        self._ensure_git_repo()
        path = self.worktree_path(run_id, task_id, role)
        branch = self.branch_name(run_id, task_id, role)
        ensure_dir(path.parent)
        if path.exists():
            self._run_git(["worktree", "remove", "--force", str(path)], check=False)
            shutil.rmtree(path, ignore_errors=True)
        base_ref = self._git_stdout(["rev-parse", "HEAD"])
        self._run_git(["worktree", "prune"], check=False)
        self._run_git(["worktree", "add", "--detach", str(path), base_ref])
        self._run_git(["checkout", "-B", branch], cwd=path)
        return str(path), branch

    def list(self) -> list[Path]:
        if not self.worktree_root.exists():
            return []
        return sorted(path for path in self.worktree_root.rglob("*") if path.is_dir() and (path / ".git").exists())

    def clean_run(self, run_id: str) -> None:
        run_root = self.worktree_root / run_id
        for path in sorted(run_root.rglob("*"), reverse=True):
            if path.is_dir() and (path / ".git").exists():
                self._run_git(["worktree", "remove", "--force", str(path)], check=False)
        shutil.rmtree(run_root, ignore_errors=True)
        self._run_git(["worktree", "prune"], check=False)

    def clean_all(self) -> None:
        for path in self.list():
            self._run_git(["worktree", "remove", "--force", str(path)], check=False)
        shutil.rmtree(self.worktree_root, ignore_errors=True)
        self.worktree_root.mkdir(parents=True, exist_ok=True)
        self._run_git(["worktree", "prune"], check=False)

    def _ensure_git_repo(self) -> None:
        if not (self.repo_root / ".git").exists():
            raise ConfigurationError(f"Repository root is not a git repository: {self.repo_root}")

    def _git_stdout(self, args: list[str], cwd: Path | None = None) -> str:
        result = self._run_git(args, cwd=cwd)
        return result.stdout.strip()

    def _run_git(self, args: list[str], cwd: Path | None = None, check: bool = True) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["git", *args],
            cwd=cwd or self.repo_root,
            check=check,
            text=True,
            capture_output=True,
        )
