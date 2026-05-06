"""Tests for cron_audit.ownership_cli."""
from __future__ import annotations

from typing import List

import pytest

from cron_audit.ownership import OwnershipRule
from cron_audit.ownership_cli import (
    has_any_unowned,
    jobs_by_team,
    print_ownership_reports,
    run_ownership,
)
from cron_audit.parser import CronJob
from cron_audit.remote_audit import AuditResult


def _make_job(command: str) -> CronJob:
    return CronJob(
        minute="0",
        hour="*",
        day_of_month="*",
        month="*",
        day_of_week="*",
        command=command,
        raw=f"0 * * * * {command}",
    )


def _success(host: str, jobs: List[CronJob]) -> AuditResult:
    return AuditResult(host=host, success=True, jobs=jobs, error=None)


def _failure(host: str) -> AuditResult:
    return AuditResult(host=host, success=False, jobs=None, error="err")


RULES = [
    OwnershipRule(pattern="/opt/backup", owner="alice", team="infra"),
    OwnershipRule(pattern="/deploy", owner="bob", team="platform"),
]


def test_run_ownership_returns_one_report_per_host():
    results = [
        _success("h1", [_make_job("/opt/backup/run.sh")]),
        _success("h2", [_make_job("/home/user/unknown.sh")]),
    ]
    reports = run_ownership(results, RULES)
    assert len(reports) == 2
    assert reports[0].host == "h1"
    assert reports[1].host == "h2"


def test_run_ownership_failure_host_has_empty_report():
    results = [_failure("bad-host")]
    reports = run_ownership(results, RULES)
    assert len(reports) == 1
    assert reports[0].total == 0


def test_has_any_unowned_true():
    results = [_success("h1", [_make_job("/mystery/cmd")])]
    reports = run_ownership(results, RULES)
    assert has_any_unowned(reports) is True


def test_has_any_unowned_false():
    results = [_success("h1", [_make_job("/opt/backup/run.sh")])]
    reports = run_ownership(results, RULES)
    assert has_any_unowned(reports) is False


def test_jobs_by_team_aggregates_correctly():
    results = [
        _success("h1", [_make_job("/opt/backup/a.sh"), _make_job("/opt/backup/b.sh")]),
        _success("h2", [_make_job("/deploy/app.sh")]),
    ]
    reports = run_ownership(results, RULES)
    counts = jobs_by_team(reports)
    assert counts["infra"] == 2
    assert counts["platform"] == 1


def test_print_ownership_reports_quiet_suppresses_fully_owned(capsys):
    results = [_success("h1", [_make_job("/opt/backup/run.sh")])]
    reports = run_ownership(results, RULES)
    print_ownership_reports(reports, quiet=True)
    captured = capsys.readouterr()
    assert captured.out.strip() == ""


def test_print_ownership_reports_quiet_shows_unowned(capsys):
    results = [_success("h1", [_make_job("/mystery/cmd")])]
    reports = run_ownership(results, RULES)
    print_ownership_reports(reports, quiet=True)
    captured = capsys.readouterr()
    assert "h1" in captured.out
