import asyncio
import subprocess
from pathlib import Path

from codex_hive.git.merge import Merger
from codex_hive.git.ops_queue import GitOpQueue
from codex_hive.git.worktrees import WorktreeManager
from codex_hive.models import WorkerResult, WorkerStatus
from tests.conftest import init_git_repo


def test_merge_queue(tmp_path: Path):
    queue = GitOpQueue(tmp_path / "lock")
    sequence: list[str] = []

    async def op(num: int):
        async def inner():
            sequence.append(f"start-{num}")
            await asyncio.sleep(0.01)
            sequence.append(f"end-{num}")
            return num
        return await queue.run(inner)

    async def main():
        await asyncio.gather(op(1), op(2), op(3))

    asyncio.run(main())
    assert len(sequence) == 6
    for index in range(0, len(sequence), 2):
        assert sequence[index].replace("start", "end") == sequence[index + 1]


def test_merger_cherry_picks_worktree_changes(tmp_path: Path):
    repo = init_git_repo(tmp_path / "repo")
    (repo / "feature.txt").write_text("base\n", encoding="utf-8")
    subprocess.run(["git", "add", "feature.txt"], cwd=repo, check=True, capture_output=True, text=True)
    subprocess.run(
        ["git", "-c", "user.name=Tests", "-c", "user.email=tests@example.invalid", "commit", "-m", "add feature"],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
    )
    manager = WorktreeManager(repo, tmp_path / "worktrees")
    worktree_path, branch_name = manager.create("run1", "impl-core", "implementer")
    worktree = Path(worktree_path)
    (worktree / "feature.txt").write_text("changed\n", encoding="utf-8")
    result = WorkerResult(
        task_id="impl-core",
        agent_id="implementer-1",
        role="implementer",
        status=WorkerStatus.succeeded,
        summary="updated feature",
        files_changed=["feature.txt"],
        branch_name=branch_name,
        worktree_path=str(worktree),
    )
    merged = Merger(repo).integrate([result])
    assert merged == ["feature.txt"]
    assert (repo / "feature.txt").read_text(encoding="utf-8") == "changed\n"
    log = subprocess.run(["git", "log", "--oneline", "--max-count=1"], cwd=repo, check=True, capture_output=True, text=True)
    assert "codex-hive: impl-core" in log.stdout
