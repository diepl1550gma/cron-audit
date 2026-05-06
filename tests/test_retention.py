"""Tests for cron_audit.retention and cron_audit.retention_cli."""
from __future__ import annotations

from typing import List, Optional

import pytest

from cron_audit.parser import CronJob
from cron_audit.remote_audit import AuditResult
from cron_audit.retention import (
    RetentionReport,
    RetentionViolation,
    check_retention,
    has_violations,
)
from cron_audit.retention_cli import (
    has_any_violations,
    run_retention_check,
)


def _job(
    command: str,
    minute: str = "0",
    hour: str = "2",
    dom: str = "*",
    month: str = "*",
    dow: str = "*",
    special: Optional[str] = None,
) -> CronJob:
    return CronJob(
        minute=minute,
        hour=hour,
        dom=dom,
        month=month,
        dow=dow,
        command=command,
        special=special,
        raw="",
    )


def _success(host: str, jobs: List[CronJob]) -> AuditResult:
    return AuditResult(host=host, success=True, jobs=jobs, error=None)


def _failure(host: str) -> AuditResult:
    return AuditResult(host=host, success=False, jobs=None, error="SSH error")


# ---------------------------------------------------------------------------
# check_retention
# ---------------------------------------------------------------------------

def test_non_retention_job_ignored():
    result = _success("host1", [_job("echo hello")])
    report = check_retention(result)
    assert not has_violations(report)
    assert report.unchecked_count == 0


def test_find_delete_with_sufficient_mtime_passes():
    result = _success("host1", [_job("find /var/log -mtime +60 -delete")])
    report = check_retention(result, min_retention_days=30)
    assert not has_violations(report)


def test_find_delete_with_insufficient_mtime_triggers_violation():
    result = _success("host1", [_job("find /var/log -mtime +7 -delete")])
    report = check_retention(result, min_retention_days=30)
    assert has_violations(report)
    assert len(report.violations) == 1
    v = report.violations[0]
    assert v.detected_days == 7
    assert v.policy_days == 30


def test_logrotate_without_mtime_increments_unchecked():
    result = _success("host1", [_job("/usr/sbin/logrotate /etc/logrotate.conf")])
    report = check_retention(result, min_retention_days=30)
    assert not has_violations(report)
    assert report.unchecked_count == 1


def test_purge_command_with_mtime_below_policy():
    result = _success("host1", [_job("purge_old_files.sh -mtime +14")])
    report = check_retention(result, min_retention_days=30)
    assert has_violations(report)


def test_failure_result_returns_empty_report():
    result = _failure("host1")
    report = check_retention(result)
    assert not has_violations(report)
    assert report.unchecked_count == 0


def test_multiple_jobs_mixed_results():
    jobs = [
        _job("find /tmp -mtime +5 -delete"),   # violation
        _job("find /tmp -mtime +90 -delete"),  # ok
        _job("logrotate /etc/logrotate.conf"),  # unchecked
        _job("echo hello"),                     # ignored
    ]
    result = _success("host1", jobs)
    report = check_retention(result, min_retention_days=30)
    assert len(report.violations) == 1
    assert report.unchecked_count == 1


# ---------------------------------------------------------------------------
# retention_cli
# ---------------------------------------------------------------------------

def test_run_retention_check_returns_one_report_per_host():
    results = [
        _success("h1", [_job("find /var -mtime +7 -delete")]),
        _success("h2", [_job("echo ok")]),
        _failure("h3"),
    ]
    reports = run_retention_check(results, min_retention_days=30)
    assert len(reports) == 3
    assert reports[0].host == "h1"
    assert has_violations(reports[0])
    assert not has_violations(reports[1])
    assert not has_violations(reports[2])


def test_has_any_violations_true():
    reports = [
        RetentionReport(host="h1"),
        RetentionReport(
            host="h2",
            violations=[
                RetentionViolation(
                    job=_job("find /tmp -mtime +1 -delete"),
                    reason="too short",
                    detected_days=1,
                    policy_days=30,
                )
            ],
        ),
    ]
    assert has_any_violations(reports)


def test_has_any_violations_false():
    reports = [RetentionReport(host="h1"), RetentionReport(host="h2")]
    assert not has_any_violations(reports)
