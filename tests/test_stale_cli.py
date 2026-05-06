"""Tests for cron_audit.stale_cli."""

from __future__ import annotations

from typing import List, Optional

from cron_audit.parser import CronJob
from cron_audit.remote_audit import AuditResult
from cron_audit.stale_cli import has_any_stale, print_stale_reports, run_stale_detection
from cron_audit.stale_detector import StalenessReport


def _make_job(command: str) -> CronJob:
    return CronJob(
        minute="0",
        hour="*",
        day_of_month="*",
        month="*",
        day_of_week="*",
        command=command,
        special=None,
    )


def _success(host: str, jobs: List[CronJob]) -> AuditResult:
    return AuditResult(host=host, success=True, jobs=jobs, error=None)


def _failure(host: str) -> AuditResult:
    return AuditResult(host=host, success=False, jobs=None, error="timeout")


def test_run_stale_detection_returns_one_report_per_host():
    results = [
        _success("host1", [_make_job("/bin/backup.sh")]),
        _success("host2", [_make_job("true")]),
    ]
    reports = run_stale_detection(results)
    assert len(reports) == 2
    assert reports[0].host == "host1"
    assert reports[1].host == "host2"


def test_run_stale_detection_failure_host_has_empty_report():
    results = [_failure("broken")]
    reports = run_stale_detection(results)
    assert len(reports) == 1
    assert reports[0].hints == []


def test_has_any_stale_true():
    results = [_success("h1", [_make_job("true")])]
    reports = run_stale_detection(results)
    assert has_any_stale(reports) is True


def test_has_any_stale_false():
    results = [_success("h1", [_make_job("/usr/bin/real_script.sh")])]
    reports = run_stale_detection(results)
    assert has_any_stale(reports) is False


def test_print_stale_reports_quiet_skips_clean(capsys):
    results = [
        _success("clean", [_make_job("/usr/bin/real.sh")]),
        _success("stale", [_make_job("true")]),
    ]
    reports = run_stale_detection(results)
    print_stale_reports(reports, quiet=True)
    captured = capsys.readouterr().out
    assert "clean" not in captured
    assert "stale" in captured


def test_print_stale_reports_shows_all_when_not_quiet(capsys):
    results = [
        _success("clean", [_make_job("/usr/bin/real.sh")]),
        _success("stale", [_make_job("true")]),
    ]
    reports = run_stale_detection(results)
    print_stale_reports(reports, quiet=False)
    captured = capsys.readouterr().out
    assert "clean" in captured
    assert "stale" in captured
