"""Retention policy checker for cron jobs.

Detects jobs whose commands suggest data retention operations (e.g. deleting
logs, rotating files) and validates them against a configured retention policy.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import List, Optional

from cron_audit.parser import CronJob
from cron_audit.remote_audit import AuditResult

_RETENTION_PATTERNS: List[re.Pattern] = [
    re.compile(r"\bfind\b.*-delete\b", re.IGNORECASE),
    re.compile(r"\bfind\b.*-exec\s+rm\b", re.IGNORECASE),
    re.compile(r"\blogrotate\b", re.IGNORECASE),
    re.compile(r"\btmpreaper\b", re.IGNORECASE),
    re.compile(r"\bclean(up)?\b", re.IGNORECASE),
    re.compile(r"\bpurge\b", re.IGNORECASE),
    re.compile(r"\barchive\b", re.IGNORECASE),
]

_MTIME_RE = re.compile(r"-mtime\s+\+(\d+)", re.IGNORECASE)


@dataclass(frozen=True)
class RetentionViolation:
    job: CronJob
    reason: str
    detected_days: Optional[int]
    policy_days: int


@dataclass
class RetentionReport:
    host: str
    violations: List[RetentionViolation] = field(default_factory=list)
    unchecked_count: int = 0


def has_violations(report: RetentionReport) -> bool:
    return len(report.violations) > 0


def _is_retention_job(job: CronJob) -> bool:
    return any(p.search(job.command) for p in _RETENTION_PATTERNS)


def _extract_mtime_days(command: str) -> Optional[int]:
    m = _MTIME_RE.search(command)
    if m:
        return int(m.group(1))
    return None


def check_retention(
    result: AuditResult,
    min_retention_days: int = 30,
) -> RetentionReport:
    """Check all jobs in an AuditResult against the retention policy."""
    report = RetentionReport(host=result.host)

    if not result.success or result.jobs is None:
        return report

    for job in result.jobs:
        if not _is_retention_job(job):
            continue

        days = _extract_mtime_days(job.command)
        if days is None:
            report.unchecked_count += 1
            continue

        if days < min_retention_days:
            report.violations.append(
                RetentionViolation(
                    job=job,
                    reason=(
                        f"Retention period {days}d is below "
                        f"minimum {min_retention_days}d"
                    ),
                    detected_days=days,
                    policy_days=min_retention_days,
                )
            )

    return report
