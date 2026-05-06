"""CLI helpers for ownership reporting across audit results."""
from __future__ import annotations

from typing import Dict, List

from cron_audit.ownership import (
    OwnershipReport,
    OwnershipRule,
    build_ownership_report,
    format_ownership_report,
)
from cron_audit.remote_audit import AuditResult


def run_ownership(
    results: List[AuditResult],
    rules: List[OwnershipRule],
) -> List[OwnershipReport]:
    """Build ownership reports for a list of audit results."""
    return [build_ownership_report(r, rules) for r in results]


def has_any_unowned(reports: List[OwnershipReport]) -> bool:
    """Return True if any report contains unowned jobs."""
    return any(len(r.unowned) > 0 for r in reports)


def jobs_by_team(reports: List[OwnershipReport]) -> Dict[str, int]:
    """Aggregate owned job counts by team across all reports."""
    counts: Dict[str, int] = {}
    for report in reports:
        for oj in report.owned:
            team = oj.team or "unknown"
            counts[team] = counts.get(team, 0) + 1
    return counts


def print_ownership_reports(
    reports: List[OwnershipReport],
    quiet: bool = False,
) -> None:
    """Print ownership reports to stdout.

    Args:
        reports: List of OwnershipReport objects.
        quiet: If True, only print reports that contain unowned jobs.
    """
    for report in reports:
        if quiet and not report.unowned:
            continue
        print(format_ownership_report(report))
        print()
