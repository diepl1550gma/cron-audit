"""Tests for cron_audit.filter_cli module."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from cron_audit.parser import CronJob
from cron_audit.remote_audit import AuditResult
from cron_audit.filter_cli import run_filter, print_filter_results, has_any_matches


def _make_job(command: str = "/bin/test", minute: str = "0", hour: str = "1") -> CronJob:
    return CronJob(
        minute=minute,
        hour=hour,
        dom="*",
        month="*",
        dow="*",
        command=command,
        special="",
        raw="",
    )


def _success(host: str, jobs) -> AuditResult:
    return AuditResult(host=host, success=True, jobs=jobs, error=None, raw="")


def _failure(host: str) -> AuditResult:
    return AuditResult(host=host, success=False, jobs=None, error="SSH error", raw="")


def test_run_filter_returns_matching_jobs():
    jobs = [_make_job("/usr/bin/backup.sh"), _make_job("/bin/cleanup")]
    results = [_success("host1", jobs)]
    filtered = run_filter(results, command_pattern="backup")
    assert "host1" in filtered
    assert len(filtered["host1"]) == 1
    assert filtered["host1"][0].command == "/usr/bin/backup.sh"


def test_run_filter_failed_host_returns_empty_list():
    results = [_failure("host2")]
    filtered = run_filter(results, command_pattern="anything")
    assert filtered["host2"] == []


def test_run_filter_no_criteria_returns_all():
    jobs = [_make_job("/bin/a"), _make_job("/bin/b")]
    results = [_success("host1", jobs)]
    filtered = run_filter(results)
    assert len(filtered["host1"]) == 2


def test_has_any_matches_true():
    filtered = {"host1": [_make_job()], "host2": []}
    assert has_any_matches(filtered) is True


def test_has_any_matches_false():
    filtered = {"host1": [], "host2": []}
    assert has_any_matches(filtered) is False


def test_print_filter_results_outputs_host(capsys):
    filtered = {"myhost": [_make_job("/bin/something")]}
    print_filter_results(filtered)
    captured = capsys.readouterr()
    assert "myhost" in captured.out
    assert "/bin/something" in captured.out


def test_print_filter_results_empty(capsys):
    filtered = {"emptyhost": []}
    print_filter_results(filtered)
    captured = capsys.readouterr()
    assert "emptyhost" in captured.out
    assert "no jobs matched" in captured.out
