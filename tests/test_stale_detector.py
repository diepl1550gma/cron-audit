"""Tests for cron_audit.stale_detector."""

from __future__ import annotations

from typing import List, Optional

import pytest

from cron_audit.parser import CronJob
from cron_audit.remote_audit import AuditResult
from cron_audit.stale_detector import (
    StalenessReport,
    detect_stale_jobs,
    has_staleness,
)


def _job(
    command: str,
    minute: str = "0",
    hour: str = "*",
    dom: str = "*",
    month: str = "*",
    dow: str = "*",
    special: Optional[str] = None,
) -> CronJob:
    return CronJob(
        minute=minute,
        hour=hour,
        day_of_month=dom,
        month=month,
        day_of_week=dow,
        command=command,
        special=special,
    )


def _success(host: str, jobs: List[CronJob]) -> AuditResult:
    return AuditResult(host=host, success=True, jobs=jobs, error=None)


def _failure(host: str) -> AuditResult:
    return AuditResult(host=host, success=False, jobs=None, error="SSH error")


def test_clean_job_has_no_hints():
    result = _success("web1", [_job("/usr/bin/backup.sh")])
    report = detect_stale_jobs(result)
    assert not has_staleness(report)
    assert report.hints == []


def test_noop_true_command_triggers_warning():
    result = _success("web1", [_job("true")])
    report = detect_stale_jobs(result)
    assert has_staleness(report)
    assert any("no-op" in h.reason for h in report.hints)
    assert report.hints[0].severity == "warning"


def test_noop_bin_false_triggers_warning():
    result = _success("web1", [_job("/bin/false")])
    report = detect_stale_jobs(result)
    assert has_staleness(report)


def test_commented_out_command_triggers_warning():
    result = _success("web1", [_job("# /old/script.sh")])
    report = detect_stale_jobs(result)
    assert has_staleness(report)
    assert any("commented" in h.reason for h in report.hints)


def test_exit_zero_command_triggers_warning():
    result = _success("web1", [_job("exit 0")])
    report = detect_stale_jobs(result)
    assert has_staleness(report)
    assert any("placeholder" in h.reason for h in report.hints)


def test_failure_result_returns_empty_report():
    result = _failure("db1")
    report = detect_stale_jobs(result)
    assert not has_staleness(report)
    assert report.host == "db1"


def test_multiple_jobs_mixed_staleness():
    jobs = [
        _job("/usr/bin/backup.sh"),
        _job("true"),
        _job("/bin/cleanup.sh"),
    ]
    result = _success("app1", jobs)
    report = detect_stale_jobs(result)
    assert has_staleness(report)
    assert len(report.hints) == 1


def test_echo_prefix_is_noop():
    result = _success("web1", [_job("echo hello world")])
    report = detect_stale_jobs(result)
    assert has_staleness(report)
