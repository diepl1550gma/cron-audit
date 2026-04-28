"""CLI integration helpers for the notification feature."""

from typing import List
from cron_audit.remote_audit import AuditResult
from cron_audit.reporter import enrich_audit_result
from cron_audit.notifier import (
    NotificationReport,
    build_notification_report,
    format_notification_report,
)


def run_notifications(results: List[AuditResult], quiet: bool = False) -> List[NotificationReport]:
    """
    Given a list of AuditResults, enrich them and produce notification reports.

    Args:
        results: List of AuditResult from audit_hosts.
        quiet:   If True, only return reports that contain warnings.

    Returns:
        List of NotificationReport, filtered by quiet flag.
    """
    reports: List[NotificationReport] = []
    for result in results:
        enriched = enrich_audit_result(result)
        report = build_notification_report(enriched)
        if quiet and not report.has_warnings:
            continue
        reports.append(report)
    return reports


def print_notification_reports(reports: List[NotificationReport]) -> None:
    """Print all notification reports to stdout."""
    if not reports:
        print("No notifications to display.")
        return
    for report in reports:
        print(format_notification_report(report))
        print()


def has_any_warnings(reports: List[NotificationReport]) -> bool:
    """Return True if any report contains at least one warning."""
    return any(r.has_warnings for r in reports)
