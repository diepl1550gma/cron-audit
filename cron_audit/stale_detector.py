"""Detect cron jobs that appear stale or inactive based on heuristics."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional

from cron_audit.parser import CronJob
from cron_audit.remote_audit import AuditResult


@dataclass
class StalenessHint:
    job: CronJob
    reason: str
    severity: str  # "warning" | "info"


@dataclass
class StalenessReport:
    host: str
    hints: List[StalenessHint] = field(default_factory=list)


def has_staleness(report: StalenessReport) -> bool:
    return len(report.hints) > 0


_STALE_COMMENT_PATTERNS = ("disabled", "todo", "fixme", "deprecated", "old", "unused")
_NOOP_COMMANDS = ("true", "false", "/bin/true", "/bin/false", ": ", "echo")


def _check_noop_command(job: CronJob) -> Optional[StalenessHint]:
    cmd = job.command.strip().lower()
    for noop in _NOOP_COMMANDS:
        if cmd == noop or cmd.startswith(noop + " "):
            return StalenessHint(
                job=job,
                reason=f"Command appears to be a no-op: {job.command!r}",
                severity="warning",
            )
    return None


def _check_commented_out_command(job: CronJob) -> Optional[StalenessHint]:
    """Detect commands wrapped in echo or commented-out via shell tricks."""
    cmd = job.command.strip()
    if cmd.startswith("#"):
        return StalenessHint(
            job=job,
            reason="Command appears to be commented out inside crontab entry",
            severity="warning",
        )
    return None


def _check_exit_zero_only(job: CronJob) -> Optional[StalenessHint]:
    cmd = job.command.strip()
    if cmd in ("exit 0", "exit"):
        return StalenessHint(
            job=job,
            reason=f"Command is just {cmd!r} — likely a placeholder",
            severity="warning",
        )
    return None


def _check_job(job: CronJob) -> List[StalenessHint]:
    hints: List[StalenessHint] = []
    for checker in (_check_noop_command, _check_commented_out_command, _check_exit_zero_only):
        result = checker(job)
        if result:
            hints.append(result)
    return hints


def detect_stale_jobs(result: AuditResult) -> StalenessReport:
    report = StalenessReport(host=result.host)
    if not result.success or result.jobs is None:
        return report
    for job in result.jobs:
        report.hints.extend(_check_job(job))
    return report
