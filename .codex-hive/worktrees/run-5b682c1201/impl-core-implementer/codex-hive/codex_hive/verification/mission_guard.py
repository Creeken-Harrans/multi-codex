"""Mission keeper checks."""

from __future__ import annotations

from ..models import MissionCheckResult, MissionSpec, WorkerResult


class MissionKeeper:
    def check(self, mission: MissionSpec, results: list[WorkerResult]) -> MissionCheckResult:
        changed = sorted({path for result in results for path in result.files_changed})
        violations = [path for path in changed if mission.scope and not any(path.startswith(item) for item in mission.scope)]
        missing = []
        lowered = " ".join(result.summary.lower() for result in results)
        category_hits = {
            "source code": any(path.startswith("codex_hive/") or path.endswith(".py") for path in changed),
            "tests": any(path.startswith("tests/") or "test" in path for path in changed),
            "documentation": any(path.startswith("docs/") or path.lower().endswith((".md", ".rst")) for path in changed),
        }
        for criterion in mission.acceptance_criteria:
            criterion_key = criterion.description.lower()
            matched = criterion_key in lowered or category_hits.get(criterion_key, False)
            if criterion.mandatory and not matched:
                missing.append(criterion.description)
        extras = [path for path in changed if mission.out_of_scope and any(path.startswith(item) for item in mission.out_of_scope)]
        score = max(0.0, 1.0 - 0.2 * len(violations) - 0.2 * len(missing) - 0.1 * len(extras))
        return MissionCheckResult(
            goal_alignment_score=round(score, 4),
            scope_violations=violations,
            missing_acceptance_items=missing,
            unjustified_extra_changes=extras,
            passed=score >= 0.6 and not violations and not missing,
        )
