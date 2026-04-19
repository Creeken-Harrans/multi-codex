"""Blind judge helpers."""

from __future__ import annotations

from ..models import WorkerResult


def anonymize_candidates(results: list[WorkerResult]) -> list[dict[str, str]]:
    return [{"candidate_id": f"candidate-{index + 1}", "summary": result.summary} for index, result in enumerate(results)]


def judge_best(results: list[WorkerResult]) -> WorkerResult:
    return max(results, key=lambda item: item.confidence)
