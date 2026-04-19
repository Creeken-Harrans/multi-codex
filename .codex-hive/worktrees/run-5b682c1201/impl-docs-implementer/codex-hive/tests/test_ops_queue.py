import asyncio
from pathlib import Path

from codex_hive.git.ops_queue import GitOpQueue


def test_ops_queue_serializes(tmp_path: Path):
    queue = GitOpQueue(tmp_path / "git.lock")
    order: list[str] = []

    async def job(name: str):
        async def op():
            order.append(f"start-{name}")
            await asyncio.sleep(0.01)
            order.append(f"end-{name}")
            return name
        return await queue.run(op)

    async def main():
        await asyncio.gather(job("a"), job("b"))

    asyncio.run(main())
    assert order in (["start-a", "end-a", "start-b", "end-b"], ["start-b", "end-b", "start-a", "end-a"])
