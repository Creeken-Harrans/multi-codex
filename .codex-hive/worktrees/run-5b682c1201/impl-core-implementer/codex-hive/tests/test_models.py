from codex_hive.models import MissionSpec, ReviewFinding, WorkerResult, WorkerStatus


def test_worker_result_schema():
    result = WorkerResult(
        task_id="t1",
        agent_id="a1",
        role="reviewer",
        status=WorkerStatus.succeeded,
        summary="done",
        confidence=0.9,
    )
    assert result.task_id == "t1"


def test_mission_spec_acceptance():
    mission = MissionSpec(mission="ship it")
    assert mission.deliverables == []


def test_review_finding_defaults():
    finding = ReviewFinding(finding_id="f1", title="Bug", description="desc")
    assert finding.severity == "medium"
