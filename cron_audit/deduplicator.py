"""Detect and report duplicate cron jobs within or across hosts."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Tuple

from cron_audit.parser import CronJob
from cron_audit.remote_audit import AuditResult


@dataclass
class DuplicateGroup:
    """A set of jobs that share the same schedule and command."""

    schedule: str
    command: str
    occurrences: List[Tuple[str, CronJob]] = field(default_factory=list)  # (host, job)

    @property
    def count(self) -> int:
        return len(self.occurrences)


@dataclass
class DeduplicationReport:
    host: str  # "<cross-host>" for multi-host reports
    duplicate_groups: List[DuplicateGroup]

    @property
    def has_duplicates(self) -> bool:
        return len(self.duplicate_groups) > 0


def _job_signature(job: CronJob) -> str:
    """Return a normalised key representing schedule + command."""
    schedule = job.special or " ".join([
        job.minute, job.hour, job.day_of_month, job.month, job.day_of_week
    ])
    return f"{schedule}|{job.command.strip()}"


def find_duplicates_in_host(host: str, jobs: List[CronJob]) -> DeduplicationReport:
    """Find duplicate jobs on a single host."""
    seen: Dict[str, DuplicateGroup] = {}
    for job in jobs:
        sig = _job_signature(job)
        if sig not in seen:
            schedule = job.special or " ".join([
                job.minute, job.hour, job.day_of_month, job.month, job.day_of_week
            ])
            seen[sig] = DuplicateGroup(schedule=schedule, command=job.command.strip())
        seen[sig].occurrences.append((host, job))

    duplicates = [g for g in seen.values() if g.count > 1]
    return DeduplicationReport(host=host, duplicate_groups=duplicates)


def find_duplicates_across_hosts(results: List[AuditResult]) -> DeduplicationReport:
    """Find jobs that appear identically on more than one host."""
    seen: Dict[str, DuplicateGroup] = {}
    for result in results:
        if not result.success or result.jobs is None:
            continue
        for job in result.jobs:
            sig = _job_signature(job)
            if sig not in seen:
                schedule = job.special or " ".join([
                    job.minute, job.hour, job.day_of_month, job.month, job.day_of_week
                ])
                seen[sig] = DuplicateGroup(schedule=schedule, command=job.command.strip())
            seen[sig].occurrences.append((result.host, job))

    duplicates = [g for g in seen.values() if g.count > 1]
    return DeduplicationReport(host="<cross-host>", duplicate_groups=duplicates)


def format_dedup_report(report: DeduplicationReport) -> str:
    """Render a DeduplicationReport as a human-readable string."""
    lines: List[str] = []
    label = f"Duplicate Cron Jobs — {report.host}"
    lines.append(label)
    lines.append("=" * len(label))
    if not report.has_duplicates:
        lines.append("No duplicates found.")
        return "\n".join(lines)
    for group in report.duplicate_groups:
        lines.append(f"\nSchedule : {group.schedule}")
        lines.append(f"Command  : {group.command}")
        lines.append(f"Count    : {group.count}")
        for host, job in group.occurrences:
            raw = job.raw_line or job.command
            lines.append(f"  [{host}] {raw}")
    return "\n".join(lines)
