"""Artifact writing."""

from __future__ import annotations

from pathlib import Path

from ..models import ArtifactIndex, RunReport
from ..utils.paths import ensure_dir
from ..utils.serialization import write_json
from .renderers import render_final_report, render_summary


class ArtifactWriter:
    def __init__(self, run_dir: Path) -> None:
        self.run_dir = ensure_dir(run_dir)
        self.tasks_dir = ensure_dir(self.run_dir / "tasks")
        self.agents_dir = ensure_dir(self.run_dir / "agents")
        self.raw_dir = ensure_dir(self.run_dir / "raw")

    def write_report(self, report: RunReport, verification_results) -> ArtifactIndex:
        files: list[str] = []
        write_json(self.run_dir / "run.json", report.model_dump(mode="json"))
        files.append("run.json")
        write_json(self.run_dir / "mission.json", report.mission.model_dump(mode="json"))
        files.append("mission.json")
        if report.consensus_report:
            write_json(self.run_dir / "consensus.json", report.consensus_report.model_dump(mode="json"))
            files.append("consensus.json")
        if report.merge_plan:
            write_json(self.run_dir / "merge-plan.json", report.merge_plan.model_dump(mode="json"))
            files.append("merge-plan.json")
        if report.mission_check:
            write_json(self.run_dir / "mission-check.json", report.mission_check.model_dump(mode="json"))
            files.append("mission-check.json")
        summary = render_summary(report)
        (self.run_dir / "summary.md").write_text(summary, encoding="utf-8")
        files.append("summary.md")
        final_report = render_final_report(report, verification_results)
        (self.run_dir / "final-report.md").write_text(final_report, encoding="utf-8")
        files.append("final-report.md")
        for result in report.worker_results:
            write_json(self.tasks_dir / f"{result.task_id}.json", result.model_dump(mode="json"))
            files.append(f"tasks/{result.task_id}.json")
        return ArtifactIndex(run_dir=str(self.run_dir), files=files)
