"""Filter cron jobs by various criteria (user, command pattern, schedule)."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import List, Optional

from cron_audit.parser import CronJob


@dataclass
class FilterCriteria:
    """Criteria used to filter a list of CronJob entries."""

    user: Optional[str] = None
    command_pattern: Optional[str] = None
    special_string: Optional[str] = None
    min_runs_per_day: Optional[float] = None
    max_runs_per_day: Optional[float] = None
    tags: List[str] = field(default_factory=list)


def filter_jobs(
    jobs: List[CronJob],
    criteria: FilterCriteria,
) -> List[CronJob]:
    """Return only the jobs that satisfy all non-None criteria."""
    result: List[CronJob] = []

    for job in jobs:
        if criteria.user is not None:
            if getattr(job, "user", None) != criteria.user:
                continue

        if criteria.command_pattern is not None:
            if not re.search(criteria.command_pattern, job.command):
                continue

        if criteria.special_string is not None:
            if job.special != criteria.special_string:
                continue

        if criteria.min_runs_per_day is not None or criteria.max_runs_per_day is not None:
            from cron_audit.scheduler import _estimate_runs_per_day

            runs = _estimate_runs_per_day(job)
            if criteria.min_runs_per_day is not None and runs < criteria.min_runs_per_day:
                continue
            if criteria.max_runs_per_day is not None and runs > criteria.max_runs_per_day:
                continue

        result.append(job)

    return result


def format_filter_summary(jobs: List[CronJob], criteria: FilterCriteria) -> str:
    """Return a human-readable summary of filtered results."""
    lines = [f"Filtered results ({len(jobs)} job(s) matched):"]
    if not jobs:
        lines.append("  (no jobs matched the given criteria)")
    for job in jobs:
        label = job.special if job.special else f"{job.minute} {job.hour} {job.dom} {job.month} {job.dow}"
        lines.append(f"  [{label}] {job.command}")
    return "\n".join(lines)
