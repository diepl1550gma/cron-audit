"""CLI helpers for the tagging feature."""

from __future__ import annotations

from typing import List

from cron_audit.remote_audit import AuditResult
from cron_audit.tagger import TaggingReport, TagRule, build_tagging_report, format_tagging_report


def run_tagging(
    audit_results: List[AuditResult],
    rules: List[TagRule],
) -> List[TaggingReport]:
    """Produce a tagging report for every successful audit result."""
    reports: List[TaggingReport] = []
    for result in audit_results:
        if result.success and result.jobs is not None:
            reports.append(build_tagging_report(result.host, result.jobs, rules))
    return reports


def print_tagging_reports(reports: List[TaggingReport]) -> None:
    """Print all tagging reports to stdout."""
    for report in reports:
        print(format_tagging_report(report))
        print()


def has_any_untagged(reports: List[TaggingReport]) -> bool:
    """Return True if any host has at least one untagged job."""
    return any(r.untagged_count > 0 for r in reports)


def jobs_by_tag(reports: List[TaggingReport], tag: str) -> List[str]:
    """Return commands from all hosts that carry a specific tag."""
    results: List[str] = []
    for report in reports:
        for tj in report.tagged_jobs:
            if tag in tj.tags:
                results.append(f"{report.host}: {tj.job.command}")
    return results
