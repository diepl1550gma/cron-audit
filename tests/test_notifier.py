"""Tests for cron_audit.notifier."""

import pytest
from unittest.mock import MagicMock
from cron_audit.notifier import (
    Notification,
    NotificationReport,
    build_notification_report,
    format_notification_report,
    HIGH_FREQUENCY_THRESHOLD,
)
from cron_audit.reporter import EnrichedJob, EnrichedAuditResult
from cron_audit.scheduler import ScheduleSummary
from cron_audit.parser import CronJob


def _make_job(command: str, runs_per_day: int = 1) -> EnrichedJob:
    job = CronJob(
        minute="0",
        hour="*",
        day_of_month="*",
        month="*",
        day_of_week="*",
        command=command,
        raw="0 * * * * " + command,
    )
    summary = ScheduleSummary(
        expression="0 * * * *",
        human_readable="every hour",
        estimated_runs_per_day=runs_per_day,
        is_special=False,
    )
    return EnrichedJob(job=job, schedule_summary=summary)


def _make_enriched(host: str, jobs=None, success=True, error=None) -> EnrichedAuditResult:
    return EnrichedAuditResult(
        host=host,
        success=success,
        enriched_jobs=jobs or [],
        error=error,
    )


def test_no_issues_produces_info_notification():
    enriched = _make_enriched("host1", jobs=[_make_job("/usr/bin/backup.sh", runs_per_day=1)])
    report = build_notification_report(enriched)
    assert not report.has_warnings
    assert any(n.level == "info" for n in report.notifications)


def test_high_frequency_job_triggers_warning():
    enriched = _make_enriched(
        "host2",
        jobs=[_make_job("/usr/bin/poll.sh", runs_per_day=HIGH_FREQUENCY_THRESHOLD)],
    )
    report = build_notification_report(enriched)
    assert report.has_warnings
    warning = next(n for n in report.notifications if n.level == "warning")
    assert "High-frequency" in warning.message
    assert warning.job_command == "/usr/bin/poll.sh"


def test_destructive_command_triggers_warning():
    enriched = _make_enriched(
        "host3",
        jobs=[_make_job("rm -rf /tmp/old_logs", runs_per_day=1)],
    )
    report = build_notification_report(enriched)
    assert report.has_warnings
    cmds = [n.message for n in report.notifications if n.level == "warning"]
    assert any("destructive" in m for m in cmds)


def test_failed_audit_produces_warning():
    enriched = _make_enriched("host4", success=False, error="Connection refused")
    report = build_notification_report(enriched)
    assert report.has_warnings
    assert report.notifications[0].level == "warning"
    assert "Connection refused" in report.notifications[0].message


def test_multiple_jobs_multiple_warnings():
    jobs = [
        _make_job("rm /var/log/app.log", runs_per_day=2),
        _make_job("/usr/bin/healthcheck.sh", runs_per_day=HIGH_FREQUENCY_THRESHOLD + 1),
    ]
    enriched = _make_enriched("host5", jobs=jobs)
    report = build_notification_report(enriched)
    warnings = [n for n in report.notifications if n.level == "warning"]
    assert len(warnings) >= 2


def test_empty_jobs_produces_info_notification():
    """An audit result with no jobs should still produce an info-level notification."""
    enriched = _make_enriched("host6", jobs=[])
    report = build_notification_report(enriched)
    assert not report.has_warnings
    assert any(n.level == "info" for n in report.notifications)
