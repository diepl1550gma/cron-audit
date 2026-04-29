"""CLI helpers for the filter feature."""

from __future__ import annotations

from typing import List, Optional

from cron_audit.filter import FilterCriteria, filter_jobs, format_filter_summary
from cron_audit.remote_audit import AuditResult
from cron_audit.reporter import enrich_audit_result


def run_filter(
    audit_results: List[AuditResult],
    user: Optional[str] = None,
    command_pattern: Optional[str] = None,
    special_string: Optional[str] = None,
    min_runs_per_day: Optional[float] = None,
    max_runs_per_day: Optional[float] = None,
) -> dict:
    """Apply filter criteria across all audit results.

    Returns a dict mapping hostname -> list of matching CronJob.
    """
    criteria = FilterCriteria(
        user=user,
        command_pattern=command_pattern,
        special_string=special_string,
        min_runs_per_day=min_runs_per_day,
        max_runs_per_day=max_runs_per_day,
    )
    output = {}
    for result in audit_results:
        if not result.success or result.jobs is None:
            output[result.host] = []
            continue
        output[result.host] = filter_jobs(result.jobs, criteria)
    return output


def print_filter_results(
    filtered: dict,
    verbose: bool = False,
) -> None:
    """Print filter results to stdout."""
    for host, jobs in filtered.items():
        print(f"\n=== {host} ===")
        from cron_audit.filter import FilterCriteria
        summary = format_filter_summary(jobs, FilterCriteria())
        print(summary)


def has_any_matches(filtered: dict) -> bool:
    """Return True if any host has at least one matching job."""
    return any(len(jobs) > 0 for jobs in filtered.values())
