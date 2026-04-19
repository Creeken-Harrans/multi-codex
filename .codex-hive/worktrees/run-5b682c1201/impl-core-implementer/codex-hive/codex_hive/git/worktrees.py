"""Git worktree management."""

from __future__ import annotations

import shutil
from pathlib import Path

from ..utils.paths import ensure_dir


class WorktreeManager:
    def __init__(self, repo_root: Path, worktree_root: Path) -> None:
        self.repo_root = repo_root
        self.worktree_root = ensure_dir(worktree_root)

    def worktree_path(self, run_id: str, task_id: str, role: str) -> Path:
        return self.worktree_root / run_id / f"{task_id}-{role}"

    def branch_name(self, run_id: str, task_id: str, role: str) -> str:
        return f"codex-hive/{run_id}/{task_id}/{role}"

    def create(self, run_id: str, task_id: str, role: str) -> tuple[str, str]:
        path = self.worktree_path(run_id, task_id, role)
        ensure_dir(path.parent)
        if path.exists():
            shutil.rmtree(path)
        shutil.copytree(self.repo_root, path, ignore=shutil.ignore_patterns(".git", ".codex-hive", "__pycache__", ".pytest_cache"))
        branch = self.branch_name(run_id, task_id, role)
        return str(path), branch

    def list(self) -> list[Path]:
        if not self.worktree_root.exists():
            return []
        return [path for path in self.worktree_root.rglob("*") if path.is_dir()]

    def clean_run(self, run_id: str) -> None:
        shutil.rmtree(self.worktree_root / run_id, ignore_errors=True)

    def clean_all(self) -> None:
        shutil.rmtree(self.worktree_root, ignore_errors=True)
        self.worktree_root.mkdir(parents=True, exist_ok=True)
