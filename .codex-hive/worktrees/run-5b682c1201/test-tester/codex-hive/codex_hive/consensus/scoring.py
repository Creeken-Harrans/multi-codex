"""Consensus scoring."""

from __future__ import annotations

from statistics import fmean

from ..models import ConsensusFinding, ConsensusLevel, ReviewFinding
from ..utils.hashing import stable_hash


def normalize_text(text: str) -> str:
    return " ".join(text.lower().split())


def canonical_key(finding: ReviewFinding) -> str:
    return stable_hash(f"{normalize_text(finding.title)}::{normalize_text(finding.description)}", length=16)


def score_finding(
    findings: list[ReviewFinding],
    total_agents: int,
    reliability_map: dict[str, float],
    confirmed_threshold: float,
    needs_verification_threshold: float,
) -> ConsensusFinding:
    first = findings[0]
    agreement_ratio = len(findings) / max(total_agents, 1)
    max_confidence = max(item.confidence for item in findings)
    evidence_count = sum(len(item.evidence) for item in findings)
    reliability_values = [reliability_map.get(item.source_agent_id or "", 0.5) for item in findings]
    reliability_factor = fmean(reliability_values) if reliability_values else 0.5
    base = agreement_ratio * max_confidence
    evidence_factor = min(1.0, evidence_count / 3)
    consensus_score = base * (0.6 + 0.2 * evidence_factor + 0.2 * reliability_factor)
    if consensus_score >= confirmed_threshold:
        level = ConsensusLevel.confirmed
    elif consensus_score >= needs_verification_threshold:
        level = ConsensusLevel.needs_verification
    else:
        level = ConsensusLevel.unverified
    return ConsensusFinding(
        canonical_key=canonical_key(first),
        title=first.title,
        normalized_description=normalize_text(first.description),
        severity=first.severity,
        evidence=[evidence for item in findings for evidence in item.evidence],
        source_agents=[item.source_agent_id or "unknown" for item in findings],
        agreement_ratio=agreement_ratio,
        max_confidence=max_confidence,
        consensus_score=round(consensus_score, 4),
        consensus_level=level,
    )
