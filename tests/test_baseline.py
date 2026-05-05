"""Tests for cron_audit.baseline."""
from __future__ import annotations

import pytest

from cron_audit.baseline import (
    BaselineReport,
    BaselineViolation,
    check_against_baseline,
    format_baseline_report,
)
from cron_audit.parser import CronJob
from cron_audit.remote_audit import AuditResult


def _job(command: str, schedule: str = "0 * * * *", user: str = "") -> CronJob:
    return CronJob(schedule=schedule, user=user or None, command=command, raw=f"{schedule} {command}")


def _success(host: str, jobs: list) -> AuditResult:
    return AuditResult(host=host, jobs=jobs, raw_crontab="", success=True, error=None)


def _failure(host: str, error: str = "timeout") -> AuditResult:
    return AuditResult(host=host, jobs=[], raw_crontab="", success=False, error=error)


def test_no_violations_when_all_approved():
    job = _job("/usr/bin/backup.sh", "0 2 * * *")
    result = _success("web-01", [job])
    baseline = [{"command": "/usr/bin/backup.sh", "schedule": "0 2 * * *"}]
    report = check_against_baseline(result, baseline)
    assert not report.has_violations
    assert report.host == "web-01"


def test_unknown_job_triggers_violation():
    job = _job("/usr/bin/unknown.sh")
    result = _success("web-01", [job])
    report = check_against_baseline(result, [])
    assert report.has_violations
    assert report.violations[0].reason == "not in baseline"


def test_schedule_mismatch_triggers_violation():
    job = _job("/usr/bin/backup.sh", "0 3 * * *")
    result = _success("web-01", [job])
    baseline = [{"command": "/usr/bin/backup.sh", "schedule": "0 2 * * *"}]
    report = check_against_baseline(result, baseline)
    assert report.has_violations
    assert "schedule changed" in report.violations[0].reason


def test_ssh_failure_skips_host():
    result = _failure("db-01", "connection refused")
    report = check_against_baseline(result, [])
    assert report.skipped
    assert "connection refused" in report.skip_reason
    assert not report.has_violations


def test_format_report_no_violations():
    report = BaselineReport(host="web-01")
    text = format_baseline_report(report)
    assert "OK" in text
    assert "web-01" in text


def test_format_report_with_violations():
    job = _job("/usr/bin/rm -rf /tmp", "* * * * *")
    v = BaselineViolation(host="web-01", job=job, reason="not in baseline")
    report = BaselineReport(host="web-01", violations=[v])
    text = format_baseline_report(report)
    assert "VIOLATION" in text
    assert "not in baseline" in text


def test_format_report_skipped():
    report = BaselineReport(host="db-01", skipped=True, skip_reason="timeout")
    text = format_baseline_report(report)
    assert "SKIPPED" in text
    assert "timeout" in text
