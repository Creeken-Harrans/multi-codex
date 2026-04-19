"""Task state machine."""

from __future__ import annotations

from collections import defaultdict

from ..models import RunStatus, TaskSpec


ALLOWED_TRANSITIONS: dict[RunStatus, set[RunStatus]] = {
    RunStatus.pending: {RunStatus.ready, RunStatus.cancelled},
    RunStatus.ready: {RunStatus.running, RunStatus.blocked, RunStatus.cancelled},
    RunStatus.blocked: {RunStatus.ready, RunStatus.failed, RunStatus.cancelled, RunStatus.escalated},
    RunStatus.running: {RunStatus.retrying, RunStatus.awaiting_merge, RunStatus.succeeded, RunStatus.failed, RunStatus.cancelled},
    RunStatus.retrying: {RunStatus.running, RunStatus.failed, RunStatus.cancelled},
    RunStatus.awaiting_approval: {RunStatus.ready, RunStatus.cancelled, RunStatus.failed},
    RunStatus.awaiting_merge: {RunStatus.running, RunStatus.succeeded, RunStatus.failed, RunStatus.escalated},
    RunStatus.succeeded: set(),
    RunStatus.failed: set(),
    RunStatus.cancelled: set(),
    RunStatus.escalated: {RunStatus.cancelled, RunStatus.failed},
}


class StateMachine:
    def transition(self, current: RunStatus, new: RunStatus) -> RunStatus:
        if new == current:
            return current
        allowed = ALLOWED_TRANSITIONS[current]
        if new not in allowed:
            raise ValueError(f"Invalid transition: {current} -> {new}")
        return new

    def dependency_ready(self, task: TaskSpec, completed: set[str]) -> bool:
        return all(dep in completed for dep in task.dependencies)

    def ready_tasks(self, tasks: list[TaskSpec], statuses: dict[str, RunStatus]) -> list[TaskSpec]:
        completed = {task_id for task_id, status in statuses.items() if status == RunStatus.succeeded}
        blocked_by: dict[str, list[str]] = defaultdict(list)
        ready: list[TaskSpec] = []
        for task in tasks:
            status = statuses.get(task.task_id, RunStatus.pending)
            if status not in {RunStatus.pending, RunStatus.ready}:
                continue
            missing = [dep for dep in task.dependencies if dep not in completed]
            if missing:
                blocked_by[task.task_id] = missing
                continue
            ready.append(task)
        return ready
