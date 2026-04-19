"""Verification output parsing."""

from __future__ import annotations

from ..models import VerificationResult


def summarize_verification(results: list[VerificationResult]) -> str:
    parts: list[str] = []
    for result in results:
        if result.skipped:
            parts.append(f"skipped: {result.reason}")
        else:
            parts.append(f"{' '.join(result.command)} => {result.returncode}")
    return "; ".join(parts)
