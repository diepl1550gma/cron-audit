"""Diff crontab snapshots across two audit runs to detect changes."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple

from cron_audit.parser import CronJob


@dataclass
class CronDiff:
    """Represents the diff between two crontab snapshots for a single host."""

    host: str
    added: List[CronJob] = field(default_factory=list)
    removed: List[CronJob] = field(default_factory=list)
    unchanged: List[CronJob] = field(default_factory=list)

    @property
    def has_changes(self) -> bool:
        return bool(self.added or self.removed)


def _job_key(job: CronJob) -> Tuple[str, str]:
    """Stable key identifying a cron job by its schedule and command."""
    return (job.schedule, job.command)


def diff_crontabs(
    host: str,
    before: List[CronJob],
    after: List[CronJob],
) -> CronDiff:
    """Compare two lists of CronJob objects and return a CronDiff.

    Args:
        host: Hostname these crontabs belong to.
        before: Snapshot from the earlier audit run.
        after: Snapshot from the more recent audit run.

    Returns:
        A CronDiff describing added, removed, and unchanged jobs.
    """
    before_map: Dict[Tuple[str, str], CronJob] = {_job_key(j): j for j in before}
    after_map: Dict[Tuple[str, str], CronJob] = {_job_key(j): j for j in after}

    before_keys: Set[Tuple[str, str]] = set(before_map)
    after_keys: Set[Tuple[str, str]] = set(after_map)

    added = [after_map[k] for k in sorted(after_keys - before_keys)]
    removed = [before_map[k] for k in sorted(before_keys - after_keys)]
    unchanged = [before_map[k] for k in sorted(before_keys & after_keys)]

    return CronDiff(host=host, added=added, removed=removed, unchanged=unchanged)


def format_diff_report(diffs: List[CronDiff]) -> str:
    """Render a human-readable diff report for a list of CronDiff objects."""
    lines: List[str] = []
    for diff in diffs:
        lines.append(f"=== {diff.host} ===")
        if not diff.has_changes:
            lines.append("  No changes detected.")
        else:
            for job in diff.added:
                lines.append(f"  + [{job.schedule}] {job.command}")
            for job in diff.removed:
                lines.append(f"  - [{job.schedule}] {job.command}")
        lines.append("")
    return "\n".join(lines).rstrip()
