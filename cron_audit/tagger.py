"""Tag cron jobs with user-defined labels based on command patterns."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import List, Optional

from cron_audit.parser import CronJob


@dataclass
class TagRule:
    """A rule that maps a regex pattern to one or more tags."""
    pattern: str
    tags: List[str]
    _compiled: re.Pattern = field(init=False, repr=False)

    def __post_init__(self) -> None:
        self._compiled = re.compile(self.pattern, re.IGNORECASE)

    def matches(self, command: str) -> bool:
        return bool(self._compiled.search(command))


@dataclass
class TaggedJob:
    """A cron job annotated with matched tags."""
    job: CronJob
    tags: List[str]

    @property
    def has_tags(self) -> bool:
        return len(self.tags) > 0


@dataclass
class TaggingReport:
    host: str
    tagged_jobs: List[TaggedJob]

    @property
    def tagged_count(self) -> int:
        return sum(1 for tj in self.tagged_jobs if tj.has_tags)

    @property
    def untagged_count(self) -> int:
        return sum(1 for tj in self.tagged_jobs if not tj.has_tags)


def tag_job(job: CronJob, rules: List[TagRule]) -> TaggedJob:
    """Apply all matching tag rules to a single job."""
    matched: List[str] = []
    for rule in rules:
        if rule.matches(job.command):
            for t in rule.tags:
                if t not in matched:
                    matched.append(t)
    return TaggedJob(job=job, tags=matched)


def tag_jobs(jobs: List[CronJob], rules: List[TagRule]) -> List[TaggedJob]:
    """Apply tag rules to a list of jobs."""
    return [tag_job(job, rules) for job in jobs]


def build_tagging_report(host: str, jobs: List[CronJob], rules: List[TagRule]) -> TaggingReport:
    """Build a full tagging report for a host."""
    return TaggingReport(host=host, tagged_jobs=tag_jobs(jobs, rules))


def format_tagging_report(report: TaggingReport) -> str:
    """Render a tagging report as a human-readable string."""
    lines = [f"=== Tag Report: {report.host} ==="]
    for tj in report.tagged_jobs:
        tag_str = ", ".join(tj.tags) if tj.has_tags else "(untagged)"
        lines.append(f"  [{tag_str}] {tj.job.command}")
    lines.append(f"  Summary: {report.tagged_count} tagged, {report.untagged_count} untagged")
    return "\n".join(lines)
