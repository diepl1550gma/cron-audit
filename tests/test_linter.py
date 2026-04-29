"""Tests for cron_audit.linter."""
import pytest
from cron_audit.linter import lint_job, lint_jobs, LintIssue
from cron_audit.parser import CronJob


def _make_job(
    command: str = "echo hello > /dev/null 2>&1",
    special: str | None = None,
    minute: str = "0",
    hour: str = "*",
    dom: str = "*",
    month: str = "*",
    dow: str = "*",
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


def test_clean_job_has_no_issues():
    result = lint_job(_make_job())
    assert result.issues == []
    assert not result.has_errors
    assert not result.has_warnings


def test_missing_output_redirect_triggers_warning():
    result = lint_job(_make_job(command="/usr/bin/backup.sh"))
    codes = [i.code for i in result.issues]
    assert "W001" in codes
    assert result.has_warnings


def test_destructive_command_triggers_error():
    result = lint_job(_make_job(command="rm -rf / > /dev/null 2>&1"))
    codes = [i.code for i in result.issues]
    assert "E001" in codes
    assert result.has_errors


def test_empty_command_triggers_error():
    result = lint_job(_make_job(command=""))
    codes = [i.code for i in result.issues]
    assert "E002" in codes
    assert result.has_errors


def test_reboot_special_triggers_info():
    result = lint_job(_make_job(command="/usr/bin/init.sh > /dev/null 2>&1", special="@reboot"))
    codes = [i.code for i in result.issues]
    assert "I001" in codes
    assert not result.has_errors
    assert not result.has_warnings


def test_lint_jobs_returns_one_result_per_job():
    jobs = [_make_job(), _make_job(command="/bin/task")]
    results = lint_jobs(jobs)
    assert len(results) == 2


def test_multiple_issues_on_same_job():
    # empty command also lacks redirect — but E002 fires first
    result = lint_job(_make_job(command="  "))
    assert result.has_errors
    codes = [i.code for i in result.issues]
    assert "E002" in codes
