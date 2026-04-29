"""Tests for cron_audit.grouper."""

from __future__ import annotations

import pytest

from cron_audit.parser import CronJob
from cron_audit.remote_audit import AuditResult
from cron_audit.grouper import (
    GroupedJobs,
    group_by_user,
    group_by_command_prefix,
    group_by_schedule,
    group_audit_results,
    format_group_report,
)


def _job(command: str, minute: str = "0", hour: str = "*",
         dom: str = "*", month: str = "*", dow: str = "*",
         special: str | None = None) -> CronJob:
    return CronJob(
        minute=minute, hour=hour, day_of_month=dom,
        month=month, day_of_week=dow, command=command,
        special=special,
    )


def _success(host: str, jobs: list) -> AuditResult:
    return AuditResult(host=host, success=True, jobs=jobs, error=None)


def _failure(host: str) -> AuditResult:
    return AuditResult(host=host, success=False, jobs=[], error="SSH error")


# ---------------------------------------------------------------------------
# group_by_user
# ---------------------------------------------------------------------------

def test_group_by_user_unknown_when_no_user_attr():
    jobs = [_job("/usr/bin/backup"), _job("/usr/bin/sync")]
    result = group_by_user(jobs)
    assert result.group_by == "user"
    assert "unknown" in result.groups
    assert result.total_jobs() == 2


# ---------------------------------------------------------------------------
# group_by_command_prefix
# ---------------------------------------------------------------------------

def test_group_by_command_prefix_splits_correctly():
    jobs = [
        _job("/usr/bin/backup --full"),
        _job("/usr/bin/backup --incremental"),
        _job("/usr/bin/sync"),
    ]
    result = group_by_command_prefix(jobs)
    assert result.group_by == "command_prefix"
    assert len(result.groups["/usr/bin/backup"]) == 2
    assert len(result.groups["/usr/bin/sync"]) == 1


def test_group_by_command_prefix_empty_command():
    jobs = [_job(""), _job("  ")]
    result = group_by_command_prefix(jobs)
    assert "(empty)" in result.groups
    assert result.total_jobs() == 2


# ---------------------------------------------------------------------------
# group_by_schedule
# ---------------------------------------------------------------------------

def test_group_by_schedule_standard():
    jobs = [
        _job("cmd_a", minute="0", hour="1"),
        _job("cmd_b", minute="0", hour="1"),
        _job("cmd_c", minute="30", hour="6"),
    ]
    result = group_by_schedule(jobs)
    assert result.group_count() == 2
    assert result.total_jobs() == 3


def test_group_by_schedule_special_string():
    jobs = [
        _job("cmd_a", special="@daily"),
        _job("cmd_b", special="@daily"),
        _job("cmd_c", special="@reboot"),
    ]
    result = group_by_schedule(jobs)
    assert "@daily" in result.groups
    assert len(result.groups["@daily"]) == 2
    assert len(result.groups["@reboot"]) == 1


# ---------------------------------------------------------------------------
# group_audit_results
# ---------------------------------------------------------------------------

def test_group_audit_results_skips_failures():
    results = [_success("host1", [_job("cmd")]), _failure("host2")]
    per_host = group_audit_results(results, mode="schedule")
    assert "host1" in per_host
    assert "host2" not in per_host


def test_group_audit_results_invalid_mode_raises():
    with pytest.raises(ValueError, match="Unknown grouping mode"):
        group_audit_results([], mode="invalid")


def test_group_audit_results_all_modes():
    jobs = [_job("/bin/true"), _job("/bin/false")]
    results = [_success("h", jobs)]
    for mode in ("schedule", "user", "command_prefix"):
        per_host = group_audit_results(results, mode=mode)
        assert "h" in per_host
        assert per_host["h"].group_by == mode


# ---------------------------------------------------------------------------
# format_group_report
# ---------------------------------------------------------------------------

def test_format_group_report_contains_host_and_commands():
    jobs = [_job("/usr/bin/backup"), _job("/usr/bin/sync")]
    grouped = group_by_command_prefix(jobs)
    report = format_group_report("myhost", grouped)
    assert "myhost" in report
    assert "/usr/bin/backup" in report
    assert "/usr/bin/sync" in report
    assert "command_prefix" in report
