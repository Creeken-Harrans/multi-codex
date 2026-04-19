"""Merge planning and execution."""

from __future__ import annotations

import subprocess
from pathlib import Path

from ..models import MergePlan, WorkerResult


class Merger:
    def __init__(self, repo_root: Path) -> None:
        self.repo_root = repo_root.resolve()

    def plan(self, run_id: str, results: list[WorkerResult]) -> MergePlan:
        branches = [result.branch_name for result in results if result.branch_name]
        actions = [f"commit worktree changes on {branch}" for branch in branches]
        actions.extend([f"cherry-pick {branch} into current branch" for branch in branches])
        return MergePlan(
            run_id=run_id,
            branch_order=[branch for branch in branches if branch],
            merge_actions=actions,
            verification_required=["run verification suite after merge"],
        )

    def integrate(self, results: list[WorkerResult]) -> list[str]:
        merged: list[str] = []
        for result in results:
            if not result.worktree_path or not result.branch_name or not result.files_changed:
                continue
            worktree_path = Path(result.worktree_path)
            if not worktree_path.exists():
                continue
            commit_sha = self._commit_worktree_changes(worktree_path, result)
            if not commit_sha:
                continue
            self._run_git(["cherry-pick", "--keep-redundant-commits", commit_sha])
            merged.extend(result.files_changed)
        return sorted(set(merged))

    def _commit_worktree_changes(self, worktree_path: Path, result: WorkerResult) -> str | None:
        changed = [path for path in result.files_changed if (worktree_path / path).exists()]
        if not changed:
            return None
        self._run_git(["add", "--", *changed], cwd=worktree_path)
        status = self._git_stdout(["status", "--porcelain", "--", *changed], cwd=worktree_path)
        if not status.strip():
            return None
        message = f"codex-hive: {result.task_id} ({result.role})"
        self._run_git(
            [
                "-c",
                "user.name=codex-hive",
                "-c",
                "user.email=codex-hive@example.invalid",
                "commit",
                "-m",
                message,
            ],
            cwd=worktree_path,
        )
        return self._git_stdout(["rev-parse", "HEAD"], cwd=worktree_path)

    def _git_stdout(self, args: list[str], cwd: Path | None = None) -> str:
        result = self._run_git(args, cwd=cwd)
        return result.stdout.strip()

    def _run_git(self, args: list[str], cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["git", *args],
            cwd=cwd or self.repo_root,
            check=True,
            text=True,
            capture_output=True,
        )
