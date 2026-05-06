"""Tests for cron_audit.ownership."""
from __future__ import annotations

from typing import List, Optional

import pytest

from cron_audit.ownership import (
    OwnedJob,
    OwnershipReport,
    OwnershipRule,
    assign_ownership,
    build_ownership_report,
    format_ownership_report,
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
    return AuditResult(host=host, success=False, jobs=None, error="SSH error")


RULES = [
    OwnershipRule(pattern="/opt/backup", owner="alice", team="infra"),
    OwnershipRule(pattern="/usr/local/bin/deploy", owner="bob", team="platform"),
]


def test_assign_ownership_matches_rule():
    jobs = [_make_job("/opt/backup/run.sh")]
    result = assign_ownership(jobs, RULES)
    assert len(result) == 1
    assert result[0].owner == "alice"
    assert result[0].team == "infra"
    assert not result[0].is_unowned


def test_assign_ownership_no_match_is_unowned():
    jobs = [_make_job("/home/user/mystery.sh")]
    result = assign_ownership(jobs, RULES)
    assert result[0].is_unowned
    assert result[0].owner is None
    assert result[0].team is None


def test_assign_ownership_case_insensitive():
    jobs = [_make_job("/OPT/BACKUP/run.sh")]
    result = assign_ownership(jobs, RULES)
    assert result[0].owner == "alice"


def test_assign_ownership_first_rule_wins():
    rules = [
        OwnershipRule(pattern="deploy", owner="first", team="A"),
        OwnershipRule(pattern="deploy", owner="second", team="B"),
    ]
    jobs = [_make_job("/usr/local/bin/deploy.sh")]
    result = assign_ownership(jobs, rules)
    assert result[0].owner == "first"


def test_build_ownership_report_success():
    jobs = [_make_job("/opt/backup/run.sh"), _make_job("/unknown/cmd")]
    result = _success("host1", jobs)
    report = build_ownership_report(result, RULES)
    assert report.host == "host1"
    assert len(report.owned) == 1
    assert len(report.unowned) == 1
    assert report.total == 2


def test_build_ownership_report_failure_returns_empty():
    result = _failure("host2")
    report = build_ownership_report(result, RULES)
    assert report.total == 0
    assert report.host == "host2"


def test_format_ownership_report_contains_host():
    jobs = [_make_job("/opt/backup/run.sh")]
    result = _success("myhost", jobs)
    report = build_ownership_report(result, RULES)
    text = format_ownership_report(report)
    assert "myhost" in text
    assert "alice" in text
    assert "infra" in text


def test_format_ownership_report_shows_unowned():
    jobs = [_make_job("/mystery/script.sh")]
    result = _success("myhost", jobs)
    report = build_ownership_report(result, RULES)
    text = format_ownership_report(report)
    assert "Unowned" in text
    assert "?/?" in text
