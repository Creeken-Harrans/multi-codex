"""Debate handling."""

from __future__ import annotations

from ..models import ConsensusReport


def apply_debate_round(report: ConsensusReport, judge_summary: str) -> ConsensusReport:
    report.debate_rounds += 1
    report.blind_judge_summary = judge_summary
    for finding in report.findings:
        finding.consensus_score = round(min(1.0, finding.consensus_score + 0.05), 4)
    report.overall_score = round(sum(item.consensus_score for item in report.findings) / max(len(report.findings), 1), 4)
    return report
