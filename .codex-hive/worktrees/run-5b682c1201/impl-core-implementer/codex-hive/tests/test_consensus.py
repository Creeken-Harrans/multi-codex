from codex_hive.consensus.merge_findings import merge_findings
from codex_hive.models import ReviewFinding


def test_consensus_scoring():
    findings = [
        ReviewFinding(finding_id="1", title="Bug", description="Same issue", evidence=["a"], confidence=0.8, source_agent_id="r1"),
        ReviewFinding(finding_id="2", title="Bug", description="Same issue", evidence=["b"], confidence=0.7, source_agent_id="r2"),
    ]
    report = merge_findings(findings, total_agents=2, reliability_map={"r1": 0.8, "r2": 0.7}, confirmed_threshold=0.75, needs_verification_threshold=0.4)
    assert len(report.findings) == 1
    assert report.findings[0].consensus_score > 0.4
