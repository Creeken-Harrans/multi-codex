"""Artifact renderers."""

from __future__ import annotations

from ..models import RunReport
from ..verification.parser import summarize_verification


def render_summary(report: RunReport, verification_summary: str = "") -> str:
    lines = [
        f"# Run {report.run_id}",
        "",
        f"Status: {report.status.value}",
        f"Strategy: {report.strategy}",
        "",
        "## Mission",
        report.mission.mission,
        "",
        "## Final Summary",
        report.final_summary or "No summary available.",
    ]
    if verification_summary:
        lines.extend(["", "## Verification", verification_summary])
    return "\n".join(lines)


def render_final_report(report: RunReport, verification_results) -> str:
    lines = [
        f"# Final Report for {report.run_id}",
        "",
        f"Mission: {report.mission.mission}",
        f"Status: {report.status.value}",
        f"Verification: {summarize_verification(verification_results)}",
        "",
        "## Worker Results",
    ]
    for result in report.worker_results:
        lines.append(f"- {result.role}/{result.task_id}: {result.summary}")
    return "\n".join(lines)
