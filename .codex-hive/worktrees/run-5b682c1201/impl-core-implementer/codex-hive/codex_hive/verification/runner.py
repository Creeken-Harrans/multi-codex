"""Verification runner."""

from __future__ import annotations

from pathlib import Path

from ..models import VerificationCommand, VerificationResult
from ..utils.subprocesses import run_command


async def run_verification(repo_root: Path, commands: list[VerificationCommand]) -> list[VerificationResult]:
    results: list[VerificationResult] = []
    for item in commands:
        result = await run_command(item.command, cwd=repo_root, timeout=300)
        results.append(
            VerificationResult(
                command=item.command,
                returncode=result.returncode,
                stdout=result.stdout,
                stderr=result.stderr,
            )
        )
    if not results:
        results.append(
            VerificationResult(
                command=[],
                returncode=0,
                stdout="",
                stderr="",
                skipped=True,
                reason="No known verification commands detected.",
            )
        )
    return results
