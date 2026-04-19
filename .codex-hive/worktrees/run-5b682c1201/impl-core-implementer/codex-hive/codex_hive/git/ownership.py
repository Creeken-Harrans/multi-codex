"""Ownership conflict detection."""

from __future__ import annotations

from collections import defaultdict

from ..models import OwnershipDecision, TaskSpec


def analyze_ownership(tasks: list[TaskSpec]) -> OwnershipDecision:
    owners: dict[str, list[str]] = defaultdict(list)
    for task in tasks:
        if not task.write_enabled:
            continue
        for owned in task.owned_paths:
            owners[owned].append(task.task_id)
    overlapping = sorted(path for path, refs in owners.items() if len(refs) > 1)
    groups: dict[str, set[str]] = defaultdict(set)
    for path, refs in owners.items():
        if len(refs) > 1:
            seed = refs[0]
            groups[seed].update(refs)
    serialized_groups = [sorted(group) for group in groups.values()]
    return OwnershipDecision(
        parallel_safe=not overlapping,
        overlapping_paths=overlapping,
        serialized_groups=serialized_groups,
    )
