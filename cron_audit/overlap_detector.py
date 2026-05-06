"""Detect scheduling overlaps between cron jobs on the same host."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Tuple

from cron_audit.parser import CronJob
from cron_audit.remote_audit import AuditResult
from cron_audit.scheduler import _estimate_runs_per_day


@dataclass
class OverlapHint:
    job_a: CronJob
    job_b: CronJob
    reason: str


@dataclass
class OverlapReport:
    host: str
    hints: List[OverlapHint] = field(default_factory=list)

    def has_overlaps(self) -> bool:
        return len(self.hints) > 0


def _schedule_signature(job: CronJob) -> str:
    """Return a normalised string representing the job's schedule fields."""
    if job.special:
        return job.special.lower()
    return " ".join([
        job.minute or "*",
        job.hour or "*",
        job.day_of_month or "*",
        job.month or "*",
        job.day_of_week or "*",
    ])


def _jobs_from_result(result: AuditResult) -> List[CronJob]:
    if not result.success or result.jobs is None:
        return []
    return result.jobs


def detect_overlaps(result: AuditResult) -> OverlapReport:
    """Identify pairs of jobs that share an identical schedule on the same host."""
    report = OverlapReport(host=result.host)
    jobs = _jobs_from_result(result)

    pairs: List[Tuple[int, int]] = []
    for i in range(len(jobs)):
        for j in range(i + 1, len(jobs)):
            sig_a = _schedule_signature(jobs[i])
            sig_b = _schedule_signature(jobs[j])
            if sig_a == sig_b:
                pairs.append((i, j))

    for i, j in pairs:
        report.hints.append(
            OverlapHint(
                job_a=jobs[i],
                job_b=jobs[j],
                reason=f"Identical schedule '{_schedule_signature(jobs[i])}'",
            )
        )

    return report


def format_overlap_report(report: OverlapReport) -> str:
    lines = [f"=== Overlap Report: {report.host} ==="]
    if not report.hints:
        lines.append("  No scheduling overlaps detected.")
    else:
        for hint in report.hints:
            lines.append(f"  [OVERLAP] {hint.reason}")
            lines.append(f"    Job A: {hint.job_a.command}")
            lines.append(f"    Job B: {hint.job_b.command}")
    return "\n".join(lines)
