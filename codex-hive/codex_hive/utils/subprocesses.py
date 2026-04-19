"""Subprocess helpers."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Sequence


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
    stream_prefix: str | None = None,
    stream_formatter: Callable[[str, str], str | None] | None = None,
) -> ProcessResult:
    process = await asyncio.create_subprocess_exec(
        *command,
        cwd=str(cwd),
        env=env,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )

    stdout_chunks: list[bytes] = []
    stderr_chunks: list[bytes] = []

    async def read_stream(stream, chunks: list[bytes], label: str) -> None:
        while True:
            line = await stream.readline()
            if not line:
                break
            chunks.append(line)
            if stream_prefix:
                text = line.decode("utf-8", errors="replace").rstrip()
                if stream_formatter:
                    formatted = stream_formatter(label, text)
                    if formatted:
                        print(f"{stream_prefix} {formatted}", flush=True)
                else:
                    print(f"{stream_prefix} {label}: {text}", flush=True)

    try:
        await asyncio.wait_for(
            asyncio.gather(
                read_stream(process.stdout, stdout_chunks, "stdout"),
                read_stream(process.stderr, stderr_chunks, "stderr"),
                process.wait(),
            ),
            timeout=timeout,
        )
    except asyncio.TimeoutError:
        process.kill()
        await process.wait()
        raise
    stdout = b"".join(stdout_chunks)
    stderr = b"".join(stderr_chunks)
    return ProcessResult(
        command=list(command),
        returncode=process.returncode,
        stdout=stdout.decode("utf-8", errors="replace"),
        stderr=stderr.decode("utf-8", errors="replace"),
    )
