"""Retry helpers."""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from typing import TypeVar

T = TypeVar("T")


async def retry_async(
    func: Callable[[], Awaitable[T]],
    retries: int = 2,
    delay_seconds: float = 0.1,
) -> T:
    last_error: Exception | None = None
    for attempt in range(retries + 1):
        try:
            return await func()
        except Exception as exc:  # pragma: no cover - generic wrapper
            last_error = exc
            if attempt >= retries:
                raise
            await asyncio.sleep(delay_seconds * (attempt + 1))
    assert last_error is not None
    raise last_error
