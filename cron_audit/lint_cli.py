"""CLI helpers for running the linter across audit results."""
from __future__ import annotations

from typing import Dict, List, Tuple

from cron_audit.linter import LintResult, lint_jobs
from cron_audit.remote_audit import AuditResult


def run_lint(
    audit_results: List[AuditResult],
) -> Dict[str, List[LintResult]]:
    """Return a mapping of host -> lint results for every successful audit."""
    report: Dict[str, List[LintResult]] = {}
    for result in audit_results:
        if result.success and result.jobs:
            report[result.host] = lint_jobs(result.jobs)
        else:
            report[result.host] = []
    return report


def has_any_errors(lint_report: Dict[str, List[LintResult]]) -> bool:
    return any(
        lr.has_errors for results in lint_report.values() for lr in results
    )


def has_any_warnings(lint_report: Dict[str, List[LintResult]]) -> bool:
    return any(
        lr.has_warnings for results in lint_report.values() for lr in results
    )


def print_lint_report(
    lint_report: Dict[str, List[LintResult]],
    errors_only: bool = False,
) -> None:
    for host, results in lint_report.items():
        filtered = [
            lr for lr in results
            if (not errors_only) or lr.has_errors
        ]
        if not filtered:
            continue
        print(f"\n=== {host} ===")
        for lr in filtered:
            label = lr.job.special or " ".join(
                [lr.job.minute or "", lr.job.hour or "",
                 lr.job.dom or "", lr.job.month or "",
                 lr.job.dow or ""]
            ).strip()
            print(f"  [{label}] {lr.job.command}")
            for issue in lr.issues:
                if errors_only and issue.severity != "error":
                    continue
                print(f"    [{issue.severity.upper()}] {issue.code}: {issue.message}")
