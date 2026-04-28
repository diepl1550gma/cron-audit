"""Tests for cron_audit.notification_cli."""

import pytest
from unittest.mock import patch, MagicMock
from cron_audit.notification_cli import (
    run_notifications,
    print_notification_reports,
    has_any_warnings,
)
from cron_audit.remote_audit import AuditResult
from cron_audit.notifier import Notification, NotificationReport
from cron_audit.parser import CronJob


def _make_audit_result(host: str, success: bool = True, jobs=None, error=None) -> AuditResult:
    return AuditResult(host=host, success=success, jobs=jobs or [], error=error)


def _make_cron_job(command: str) -> CronJob:
    return CronJob(
        minute="0",
        hour="1",
        day_of_month="*",
        month="*",
        day_of_week="*",
        command=command,
        raw=f"0 1 * * * {command}",
    )


def test_run_notifications_returns_one_per_host():
    results = [
        _make_audit_result("host1", jobs=[_make_cron_job("/bin/backup.sh")]),
        _make_audit_result("host2", jobs=[_make_cron_job("/bin/cleanup.sh")]),
    ]
    reports = run_notifications(results)
    assert len(reports) == 2
    hosts = {r.host for r in reports}
    assert hosts == {"host1", "host2"}


def test_run_notifications_quiet_filters_non_warnings():
    results = [
        _make_audit_result("host1", jobs=[_make_cron_job("/bin/safe.sh")]),
        _make_audit_result("host2", success=False, error="timeout"),
    ]
    reports = run_notifications(results, quiet=True)
    # Only host2 should appear (has a warning due to failure)
    assert len(reports) == 1
    assert reports[0].host == "host2"


def test_has_any_warnings_true():
    reports = [
        NotificationReport(
            host="h1",
            notifications=[Notification(level="warning", host="h1", message="bad")],
        )
    ]
    assert has_any_warnings(reports) is True


def test_has_any_warnings_false():
    reports = [
        NotificationReport(
            host="h1",
            notifications=[Notification(level="info", host="h1", message="ok")],
        )
    ]
    assert has_any_warnings(reports) is False


def test_has_any_warnings_empty():
    assert has_any_warnings([]) is False


def test_print_notification_reports_no_reports(capsys):
    print_notification_reports([])
    captured = capsys.readouterr()
    assert "No notifications" in captured.out


def test_print_notification_reports_outputs_host(capsys):
    reports = [
        NotificationReport(
            host="myhost",
            notifications=[Notification(level="info", host="myhost", message="All clear")],
        )
    ]
    print_notification_reports(reports)
    captured = capsys.readouterr()
    assert "myhost" in captured.out
    assert "All clear" in captured.out
