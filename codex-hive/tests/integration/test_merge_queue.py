import asyncio
from pathlib import Path

from codex_hive.git.ops_queue import GitOpQueue


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
