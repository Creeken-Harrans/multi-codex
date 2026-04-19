"""Consensus report rendering."""

from __future__ import annotations

from ..models import ConsensusReport


def render_consensus_markdown(report: ConsensusReport) -> str:
    lines = ["# Consensus Report", ""]
    lines.append(f"Overall score: {report.overall_score:.2f}")
    if report.blind_judge_summary:
        lines.append(f"Judge summary: {report.blind_judge_summary}")
    lines.append("")
    for finding in report.findings:
        lines.append(f"- {finding.title} [{finding.consensus_level}] score={finding.consensus_score:.2f}")
    return "\n".join(lines)
