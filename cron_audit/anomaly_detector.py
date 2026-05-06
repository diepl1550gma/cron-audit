"""Detect anomalous cron jobs based on unusual scheduling patterns or commands."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List

from cron_audit.remote_audit import AuditResult
from cron_audit.parser import CronJob


@dataclass
class AnomalyHint:
    job: CronJob
    reason: str
    severity: str  # "low" | "medium" | "high"


@dataclass
class AnomalyReport:
    host: str
    anomalies: List[AnomalyHint] = field(default_factory=list)


def has_anomalies(report: AnomalyReport) -> bool:
    return len(report.anomalies) > 0


_SUSPICIOUS_COMMANDS = [
    "curl", "wget", "nc", "ncat", "bash -i", "sh -i",
    "python -c", "perl -e", "ruby -e",
]

_UNUSUAL_HOURS = set(range(0, 5))  # midnight to 4 AM


def _check_suspicious_command(job: CronJob) -> AnomalyHint | None:
    cmd = job.command.lower()
    for pattern in _SUSPICIOUS_COMMANDS:
        if pattern in cmd:
            return AnomalyHint(
                job=job,
                reason=f"Command contains suspicious pattern: '{pattern}'",
                severity="high",
            )
    return None


def _check_unusual_hour(job: CronJob) -> AnomalyHint | None:
    if job.special:
        return None
    hour_field = job.hour
    if hour_field == "*":
        return None
    try:
        hour = int(hour_field)
        if hour in _UNUSUAL_HOURS:
            return AnomalyHint(
                job=job,
                reason=f"Job scheduled during unusual hour: {hour:02d}:xx",
                severity="low",
            )
    except ValueError:
        pass
    return None


def _check_every_minute(job: CronJob) -> AnomalyHint | None:
    if job.special:
        return None
    if all(f == "*" for f in [job.minute, job.hour, job.day, job.month, job.weekday]):
        return AnomalyHint(
            job=job,
            reason="Job runs every minute (* * * * *), which is rarely intentional",
            severity="medium",
        )
    return None


_CHECKS = [_check_suspicious_command, _check_unusual_hour, _check_every_minute]


def detect_anomalies(result: AuditResult) -> AnomalyReport:
    report = AnomalyReport(host=result.host)
    if not result.success or result.jobs is None:
        return report
    for job in result.jobs:
        for check in _CHECKS:
            hint = check(job)
            if hint is not None:
                report.anomalies.append(hint)
    return report
