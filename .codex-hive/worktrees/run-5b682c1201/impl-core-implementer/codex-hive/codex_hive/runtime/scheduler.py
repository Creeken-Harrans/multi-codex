"""Task scheduler."""

from __future__ import annotations

from collections import deque

from ..models import OwnershipDecision, TaskSpec


class Scheduler:
    def order(self, tasks: list[TaskSpec], ownership: OwnershipDecision) -> list[TaskSpec]:
        if ownership.parallel_safe:
            return tasks
        group_map = {task_id: index for index, group in enumerate(ownership.serialized_groups) for task_id in group}
        return sorted(tasks, key=lambda task: group_map.get(task.task_id, 999))

    def batch(self, tasks: list[TaskSpec], max_parallel: int) -> list[list[TaskSpec]]:
        queue = deque(tasks)
        batches: list[list[TaskSpec]] = []
        while queue:
            batch: list[TaskSpec] = []
            while queue and len(batch) < max_parallel:
                batch.append(queue.popleft())
            batches.append(batch)
        return batches
