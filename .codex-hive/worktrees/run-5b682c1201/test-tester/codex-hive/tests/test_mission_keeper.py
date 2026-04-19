from codex_hive.models import AcceptanceCriteria, MissionSpec, WorkerResult, WorkerStatus
from codex_hive.verification.mission_guard import MissionKeeper


def test_mission_keeper_pass():
    mission = MissionSpec(
        mission="ship code",
        scope=["codex_hive"],
        acceptance_criteria=[AcceptanceCriteria(description="source code")],
    )
    result = WorkerResult(task_id="1", agent_id="a", role="implementer", status=WorkerStatus.succeeded, summary="source code complete", files_changed=["codex_hive/x.py"], confidence=0.9)
    check = MissionKeeper().check(mission, [result])
    assert check.passed is True


def test_mission_keeper_fail():
    mission = MissionSpec(
        mission="ship code",
        scope=["codex_hive"],
        acceptance_criteria=[AcceptanceCriteria(description="tests")],
    )
    result = WorkerResult(task_id="1", agent_id="a", role="implementer", status=WorkerStatus.succeeded, summary="source code complete", files_changed=["docs/x.md"], confidence=0.9)
    check = MissionKeeper().check(mission, [result])
    assert check.passed is False


def test_mission_keeper_accepts_path_evidence():
    mission = MissionSpec(
        mission="ship code",
        scope=["codex_hive", "tests", "docs"],
        acceptance_criteria=[
            AcceptanceCriteria(description="source code"),
            AcceptanceCriteria(description="tests"),
            AcceptanceCriteria(description="documentation"),
        ],
    )
    results = [
        WorkerResult(task_id="1", agent_id="a", role="implementer", status=WorkerStatus.succeeded, summary="core complete", files_changed=["codex_hive/runtime/x.py"], confidence=0.9),
        WorkerResult(task_id="2", agent_id="b", role="tester", status=WorkerStatus.succeeded, summary="verification complete", files_changed=["tests/test_x.py"], confidence=0.9),
        WorkerResult(task_id="3", agent_id="c", role="implementer", status=WorkerStatus.succeeded, summary="docs complete", files_changed=["docs/x.md"], confidence=0.9),
    ]
    check = MissionKeeper().check(mission, results)
    assert check.passed is True
