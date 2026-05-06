"""Tests for cron_audit.dependency_detector."""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from cron_audit.dependency_detector import (
    DependencyReport,
    build_dependency_reports,
    detect_dependencies,
    format_dependency_report,
    has_dependencies,
)
from cron_audit.parser import CronJob
from cron_audit.remote_audit import AuditResult


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _job(command: str) -> CronJob:
    return CronJob(
        minute="0",
        hour="*",
        day_of_month="*",
        month="*",
        day_of_week="*",
        command=command,
    )


def _success(host: str, jobs: list) -> AuditResult:
    return AuditResult(host=host, success=True, jobs=jobs, error=None)


def _failure(host: str) -> AuditResult:
    return AuditResult(host=host, success=False, jobs=None, error="SSH error")


# ---------------------------------------------------------------------------
# detect_dependencies
# ---------------------------------------------------------------------------

def test_no_shared_paths_returns_no_hints():
    jobs = [_job("/usr/bin/backup"), _job("/usr/bin/cleanup")]
    hints = detect_dependencies(jobs)
    assert hints == []


def test_shared_path_detected():
    jobs = [
        _job("/data/export/run.sh"),
        _job("/data/export/compress.sh"),
    ]
    hints = detect_dependencies(jobs)
    assert len(hints) == 1
    assert "/data/export" in hints[0].reason or "shared path" in hints[0].reason


def test_multiple_shared_paths_produce_one_hint_per_pair():
    jobs = [
        _job("/var/log/rotate.sh /tmp/work"),
        _job("/var/log/archive.sh /tmp/work"),
        _job("/home/user/unrelated.sh"),
    ]
    hints = detect_dependencies(jobs)
    # job 0 & 1 share /var/log and /tmp/work → at least one hint
    assert any(
        h.job_a.command == jobs[0].command and h.job_b.command == jobs[1].command
        for h in hints
    )


def test_single_job_no_hints():
    assert detect_dependencies([_job("/usr/bin/do_thing")]) == []


def test_empty_jobs_no_hints():
    assert detect_dependencies([]) == []


# ---------------------------------------------------------------------------
# has_dependencies
# ---------------------------------------------------------------------------

def test_has_dependencies_true():
    report = DependencyReport(host="h", hints=[MagicMock()])
    assert has_dependencies(report) is True


def test_has_dependencies_false():
    report = DependencyReport(host="h", hints=[])
    assert has_dependencies(report) is False


# ---------------------------------------------------------------------------
# build_dependency_reports
# ---------------------------------------------------------------------------

def test_build_reports_skips_failures():
    results = [_failure("bad-host")]
    reports = build_dependency_reports(results)
    assert len(reports) == 1
    assert reports[0].host == "bad-host"
    assert reports[0].hints == []


def test_build_reports_success_with_shared_path():
    jobs = [_job("/opt/scripts/a.sh"), _job("/opt/scripts/b.sh")]
    results = [_success("web01", jobs)]
    reports = build_dependency_reports(results)
    assert reports[0].host == "web01"
    assert len(reports[0].hints) >= 1


def test_build_reports_multiple_hosts():
    results = [
        _success("h1", [_job("/a/x"), _job("/a/y")]),
        _success("h2", [_job("/z/only")]),
    ]
    reports = build_dependency_reports(results)
    assert len(reports) == 2
    assert any(r.host == "h1" and r.hints for r in reports)
    assert any(r.host == "h2" and not r.hints for r in reports)


# ---------------------------------------------------------------------------
# format_dependency_report
# ---------------------------------------------------------------------------

def test_format_no_hints():
    report = DependencyReport(host="clean-host", hints=[])
    output = format_dependency_report(report)
    assert "clean-host" in output
    assert "No dependency hints" in output


def test_format_with_hints():
    jobs = [_job("/data/run.sh"), _job("/data/archive.sh")]
    hints = detect_dependencies(jobs)
    report = DependencyReport(host="prod01", hints=hints)
    output = format_dependency_report(report)
    assert "prod01" in output
    assert "/data/run.sh" in output or "/data/archive.sh" in output
