import pytest

from codex_hive.models import RunStatus, TaskSpec, TaskType
from codex_hive.runtime.state_machine import StateMachine


def test_transition_valid():
    machine = StateMachine()
    assert machine.transition(RunStatus.pending, RunStatus.ready) == RunStatus.ready


def test_transition_invalid():
    machine = StateMachine()
    with pytest.raises(ValueError):
        machine.transition(RunStatus.pending, RunStatus.succeeded)


def test_ready_tasks_dependency():
    machine = StateMachine()
    tasks = [
        TaskSpec(task_id="a", title="a", description="a", type=TaskType.exploration, role="scout"),
        TaskSpec(task_id="b", title="b", description="b", type=TaskType.review, role="reviewer", dependencies=["a"]),
    ]
    ready = machine.ready_tasks(tasks, {"a": RunStatus.succeeded, "b": RunStatus.pending})
    assert [item.task_id for item in ready] == ["b"]
