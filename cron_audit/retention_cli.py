"""CLI helpers for the retention policy checker."""
from __future__ import annotations

from typing import List

from cron_audit.remote_audit import AuditResult
from cron_audit.retention import RetentionReport, check_retention, has_violations


def run_retention_check(
    results: List[AuditResult],
    min_retention_days: int = 30,
) -> List[RetentionReport]:
    """Run the retention check across all audit results."""
    return [
        check_retention(result, min_retention_days=min_retention_days)
        for result in results
    ]


def has_any_violations(reports: List[RetentionReport]) -> bool:
    return any(has_violations(r) for r in reports)


def print_retention_reports(
    reports: List[RetentionReport],
    only_violations: bool = False,
) -> None:
    for report in reports:
        if only_violations and not has_violations(report):
            continue

        print(f"\n=== Retention Report: {report.host} ===")

        if not report.violations and report.unchecked_count == 0:
            print("  No retention jobs detected.")
            continue

        if report.violations:
            print(f"  Violations ({len(report.violations)}):")
            for v in report.violations:
                print(f"    [VIOLATION] {v.job.command}")
                print(f"      Reason : {v.reason}")
                print(
                    f"      Schedule: {v.job.special or ' '.join([
                        v.job.minute, v.job.hour, v.job.dom,
                        v.job.month, v.job.dow
                    ])}"
                )
        else:
            print("  No policy violations found.")

        if report.unchecked_count:
            print(
                f"  Unchecked retention jobs (no -mtime): "
                f"{report.unchecked_count}"
            )
