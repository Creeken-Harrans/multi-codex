"""Serialized git operation queue."""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from pathlib import Path
from typing import TypeVar

from ..locks import FileLock

T = TypeVar("T")


class GitOpQueue:
    def __init__(self, lock_path: Path) -> None:
        self.lock = FileLock(lock_path)

    async def run(self, operation: Callable[[], Awaitable[T]]) -> T:
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, self.lock.acquire)
        try:
            return await operation()
        finally:
            await loop.run_in_executor(None, self.lock.release)
