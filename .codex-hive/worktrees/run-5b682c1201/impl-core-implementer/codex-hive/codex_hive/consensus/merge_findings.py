"""Merge similar findings into consensus findings."""

from __future__ import annotations

from collections import defaultdict

from ..models import ConsensusReport, ReviewFinding
from .scoring import canonical_key, score_finding


def merge_findings(
    findings: list[ReviewFinding],
    total_agents: int,
    reliability_map: dict[str, float],
    confirmed_threshold: float,
    needs_verification_threshold: float,
) -> ConsensusReport:
    grouped: dict[str, list[ReviewFinding]] = defaultdict(list)
    for finding in findings:
        grouped[canonical_key(finding)].append(finding)
    consensus_findings = [
        score_finding(group, total_agents, reliability_map, confirmed_threshold, needs_verification_threshold)
        for group in grouped.values()
    ]
    overall = sum(item.consensus_score for item in consensus_findings) / max(len(consensus_findings), 1)
    return ConsensusReport(findings=consensus_findings, overall_score=round(overall, 4))
