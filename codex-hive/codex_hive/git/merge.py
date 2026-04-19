"""Merge planning and execution."""

from __future__ import annotations

import shutil
from pathlib import Path

from ..models import MergePlan, WorkerResult


class Merger:
    def __init__(self, repo_root: Path) -> None:
        self.repo_root = repo_root

    def plan(self, run_id: str, results: list[WorkerResult]) -> MergePlan:
        branches = [result.branch_name for result in results if result.branch_name]
        actions = [f"merge {branch}" for branch in branches]
        return MergePlan(
            run_id=run_id,
            branch_order=[branch for branch in branches if branch],
            merge_actions=actions,
            verification_required=["run verification suite after merge"],
        )

    def integrate(self, results: list[WorkerResult]) -> list[str]:
        merged: list[str] = []
        for result in results:
            worktree_path = Path(result.worktree_path) if result.worktree_path else None
            if worktree_path and worktree_path.exists():
                for changed in result.files_changed:
                    source = worktree_path / changed
                    target = self.repo_root / changed
                    if source.exists():
                        target.parent.mkdir(parents=True, exist_ok=True)
                        shutil.copy2(source, target)
                        merged.append(changed)
        return sorted(set(merged))
