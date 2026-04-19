"""Subprocess helpers."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence


@dataclass(slots=True)
class ProcessResult:
    command: list[str]
    returncode: int
    stdout: str
    stderr: str


async def run_command(
    command: Sequence[str],
    cwd: Path,
    env: dict[str, str] | None = None,
    timeout: float | None = None,
) -> ProcessResult:
    process = await asyncio.create_subprocess_exec(
        *command,
        cwd=str(cwd),
        env=env,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    try:
        stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=timeout)
    except asyncio.TimeoutError:
        process.kill()
        await process.wait()
        raise
    return ProcessResult(
        command=list(command),
        returncode=process.returncode,
        stdout=stdout.decode("utf-8", errors="replace"),
        stderr=stderr.decode("utf-8", errors="replace"),
    )
