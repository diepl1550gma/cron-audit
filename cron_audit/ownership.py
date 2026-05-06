"""Ownership mapping: associate cron jobs with team/owner metadata."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional

from cron_audit.parser import CronJob
from cron_audit.remote_audit import AuditResult


@dataclass
class OwnershipRule:
    """Maps a command pattern (substring) to an owner and team."""
    pattern: str
    owner: str
    team: str


@dataclass
class OwnedJob:
    job: CronJob
    owner: Optional[str]
    team: Optional[str]

    @property
    def is_unowned(self) -> bool:
        return self.owner is None


@dataclass
class OwnershipReport:
    host: str
    owned: List[OwnedJob] = field(default_factory=list)
    unowned: List[OwnedJob] = field(default_factory=list)

    @property
    def total(self) -> int:
        return len(self.owned) + len(self.unowned)


def _match_rule(command: str, rules: List[OwnershipRule]) -> Optional[OwnershipRule]:
    """Return the first rule whose pattern appears in the command."""
    for rule in rules:
        if rule.pattern.lower() in command.lower():
            return rule
    return None


def assign_ownership(
    jobs: List[CronJob],
    rules: List[OwnershipRule],
) -> List[OwnedJob]:
    """Assign owner/team to each job using the provided rules."""
    result: List[OwnedJob] = []
    for job in jobs:
        rule = _match_rule(job.command, rules)
        result.append(
            OwnedJob(
                job=job,
                owner=rule.owner if rule else None,
                team=rule.team if rule else None,
            )
        )
    return result


def build_ownership_report(
    result: AuditResult,
    rules: List[OwnershipRule],
) -> OwnershipReport:
    """Build an OwnershipReport for a single AuditResult."""
    report = OwnershipReport(host=result.host)
    if not result.success or result.jobs is None:
        return report
    for owned_job in assign_ownership(result.jobs, rules):
        if owned_job.is_unowned:
            report.unowned.append(owned_job)
        else:
            report.owned.append(owned_job)
    return report


def format_ownership_report(report: OwnershipReport) -> str:
    """Render an ownership report as a human-readable string."""
    lines = [f"=== Ownership Report: {report.host} ==="]
    lines.append(f"Total jobs: {report.total}  Owned: {len(report.owned)}  Unowned: {len(report.unowned)}")
    if report.owned:
        lines.append("\nOwned jobs:")
        for oj in report.owned:
            lines.append(f"  [{oj.team}/{oj.owner}] {oj.job.command}")
    if report.unowned:
        lines.append("\nUnowned jobs:")
        for oj in report.unowned:
            lines.append(f"  [?/?] {oj.job.command}")
    return "\n".join(lines)
