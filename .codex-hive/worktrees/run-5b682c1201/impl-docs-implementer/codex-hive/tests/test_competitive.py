from codex_hive.consensus.blind_judge import judge_best
from codex_hive.models import WorkerResult, WorkerStatus


def test_judge_best():
    best = judge_best(
        [
            WorkerResult(task_id="a", agent_id="1", role="implementer", status=WorkerStatus.succeeded, summary="a", confidence=0.7),
            WorkerResult(task_id="b", agent_id="2", role="implementer", status=WorkerStatus.succeeded, summary="b", confidence=0.9),
        ]
    )
    assert best.task_id == "b"
