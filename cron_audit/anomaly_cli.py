"""CLI helpers for anomaly detection across audited hosts."""
from __future__ import annotations

from typing import List

from cron_audit.remote_audit import AuditResult
from cron_audit.anomaly_detector import AnomalyReport, detect_anomalies, has_anomalies


def run_anomaly_detection(results: List[AuditResult]) -> List[AnomalyReport]:
    """Run anomaly detection over a list of audit results."""
    return [detect_anomalies(r) for r in results]


def has_any_anomalies(reports: List[AnomalyReport]) -> bool:
    """Return True if any report contains at least one anomaly."""
    return any(has_anomalies(r) for r in reports)


def print_anomaly_reports(
    reports: List[AnomalyReport],
    quiet: bool = False,
) -> None:
    """Print anomaly reports to stdout.

    Args:
        reports: List of AnomalyReport objects to display.
        quiet:   If True, only print hosts that have anomalies.
    """
    for report in reports:
        if quiet and not has_anomalies(report):
            continue
        print(f"\n[{report.host}]")
        if not has_anomalies(report):
            print("  No anomalies detected.")
            continue
        for hint in report.anomalies:
            cmd_preview = hint.job.command[:60]
            severity_label = hint.severity.upper()
            print(f"  [{severity_label}] {hint.reason}")
            print(f"         command: {cmd_preview}")
            schedule = (
                hint.job.special
                if hint.job.special
                else (
                    f"{hint.job.minute} {hint.job.hour} "
                    f"{hint.job.day} {hint.job.month} {hint.job.weekday}"
                )
            )
            print(f"         schedule: {schedule}")
