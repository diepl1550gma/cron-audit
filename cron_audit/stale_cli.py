"""CLI helpers for stale job detection."""

from __future__ import annotations

from typing import List

from cron_audit.remote_audit import AuditResult
from cron_audit.stale_detector import StalenessReport, detect_stale_jobs, has_staleness


def run_stale_detection(results: List[AuditResult]) -> List[StalenessReport]:
    """Run stale detection across all audit results."""
    return [detect_stale_jobs(r) for r in results]


def has_any_stale(reports: List[StalenessReport]) -> bool:
    """Return True if any host has at least one staleness hint."""
    return any(has_staleness(r) for r in reports)


def print_stale_reports(reports: List[StalenessReport], quiet: bool = False) -> None:
    """Print staleness reports to stdout."""
    for report in reports:
        if quiet and not has_staleness(report):
            continue
        print(f"\n[{report.host}]")
        if not report.hints:
            print("  No stale jobs detected.")
            continue
        for hint in report.hints:
            tag = hint.severity.upper()
            schedule = getattr(hint.job, "special", None) or " ".join([
                hint.job.minute, hint.job.hour,
                hint.job.day_of_month, hint.job.month, hint.job.day_of_week,
            ])
            print(f"  [{tag}] {schedule} {hint.job.command}")
            print(f"         Reason: {hint.reason}")
