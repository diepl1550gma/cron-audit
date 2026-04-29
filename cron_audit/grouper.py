"""Group cron jobs by various attributes for reporting and analysis."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from typing import Dict, List

from cron_audit.parser import CronJob
from cron_audit.remote_audit import AuditResult


@dataclass
class GroupedJobs:
    """Jobs grouped by a specific key."""
    group_by: str
    groups: Dict[str, List[CronJob]] = field(default_factory=dict)

    def total_jobs(self) -> int:
        return sum(len(jobs) for jobs in self.groups.values())

    def group_count(self) -> int:
        return len(self.groups)


def group_by_user(jobs: List[CronJob]) -> GroupedJobs:
    """Group jobs by the user field (if available) or 'unknown'."""
    groups: Dict[str, List[CronJob]] = defaultdict(list)
    for job in jobs:
        user = getattr(job, "user", None) or "unknown"
        groups[user].append(job)
    return GroupedJobs(group_by="user", groups=dict(groups))


def group_by_command_prefix(jobs: List[CronJob], max_prefix_len: int = 20) -> GroupedJobs:
    """Group jobs by a normalised prefix of their command."""
    groups: Dict[str, List[CronJob]] = defaultdict(list)
    for job in jobs:
        prefix = job.command.strip().split()[0] if job.command.strip() else "(empty)"
        prefix = prefix[:max_prefix_len]
        groups[prefix].append(job)
    return GroupedJobs(group_by="command_prefix", groups=dict(groups))


def group_by_schedule(jobs: List[CronJob]) -> GroupedJobs:
    """Group jobs by their raw schedule expression."""
    groups: Dict[str, List[CronJob]] = defaultdict(list)
    for job in jobs:
        schedule = job.special if job.special else " ".join(
            [job.minute, job.hour, job.day_of_month, job.month, job.day_of_week]
        )
        groups[schedule].append(job)
    return GroupedJobs(group_by="schedule", groups=dict(groups))


def group_audit_results(
    results: List[AuditResult],
    mode: str = "schedule",
) -> Dict[str, GroupedJobs]:
    """Return a per-host GroupedJobs mapping for all successful audit results.

    mode must be one of 'schedule', 'user', or 'command_prefix'.
    """
    if mode not in ("schedule", "user", "command_prefix"):
        raise ValueError(f"Unknown grouping mode: {mode!r}")

    per_host: Dict[str, GroupedJobs] = {}
    for result in results:
        if not result.success or result.jobs is None:
            continue
        if mode == "schedule":
            per_host[result.host] = group_by_schedule(result.jobs)
        elif mode == "user":
            per_host[result.host] = group_by_user(result.jobs)
        else:
            per_host[result.host] = group_by_command_prefix(result.jobs)
    return per_host


def format_group_report(host: str, grouped: GroupedJobs) -> str:
    """Render a simple text report for a single host's grouped jobs."""
    lines = [f"Host: {host}  (grouped by {grouped.group_by})",
             f"  Groups : {grouped.group_count()}",
             f"  Total  : {grouped.total_jobs()} job(s)",
             ""]
    for key, jobs in sorted(grouped.groups.items()):
        lines.append(f"  [{key}]  — {len(jobs)} job(s)")
        for job in jobs:
            lines.append(f"    {job.command}")
    return "\n".join(lines)
