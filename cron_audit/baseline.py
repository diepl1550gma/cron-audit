"""Baseline comparison: compare current audit results against a known-good baseline."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional

from cron_audit.parser import CronJob
from cron_audit.remote_audit import AuditResult


@dataclass
class BaselineViolation:
    host: str
    job: CronJob
    reason: str


@dataclass
class BaselineReport:
    host: str
    violations: List[BaselineViolation] = field(default_factory=list)
    skipped: bool = False
    skip_reason: str = ""

    @property
    def has_violations(self) -> bool:
        return bool(self.violations)


def _job_key(job: CronJob) -> str:
    """Stable key for a cron job used in baseline lookups."""
    return f"{job.user or ''}|{job.command}"


def check_against_baseline(
    result: AuditResult,
    baseline_jobs: List[Dict],
) -> BaselineReport:
    """Return a BaselineReport comparing *result* jobs against *baseline_jobs*.

    baseline_jobs is a list of dicts with keys: user (optional), command, schedule.
    """
    if not result.success:
        return BaselineReport(
            host=result.host,
            skipped=True,
            skip_reason=result.error or "SSH failure",
        )

    approved: Dict[str, Dict] = {}
    for entry in baseline_jobs:
        key = f"{entry.get('user', '')}|{entry['command']}"
        approved[key] = entry

    violations: List[BaselineViolation] = []
    for job in result.jobs:
        key = _job_key(job)
        if key not in approved:
            violations.append(
                BaselineViolation(host=result.host, job=job, reason="not in baseline")
            )
        else:
            expected_schedule = approved[key].get("schedule")
            if expected_schedule and job.schedule != expected_schedule:
                violations.append(
                    BaselineViolation(
                        host=result.host,
                        job=job,
                        reason=f"schedule changed (expected '{expected_schedule}', got '{job.schedule}')",
                    )
                )

    return BaselineReport(host=result.host, violations=violations)


def format_baseline_report(report: BaselineReport) -> str:
    """Return a human-readable string for a BaselineReport."""
    lines: List[str] = [f"=== Baseline: {report.host} ==="]
    if report.skipped:
        lines.append(f"  SKIPPED: {report.skip_reason}")
        return "\n".join(lines)
    if not report.has_violations:
        lines.append("  OK — all jobs match baseline.")
    else:
        for v in report.violations:
            lines.append(f"  VIOLATION [{v.reason}]: {v.job.schedule} {v.job.command}")
    return "\n".join(lines)
