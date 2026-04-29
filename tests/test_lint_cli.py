"""Tests for cron_audit.lint_cli."""
from unittest.mock import patch
from cron_audit.lint_cli import run_lint, has_any_errors, has_any_warnings, print_lint_report
from cron_audit.remote_audit import AuditResult
from cron_audit.parser import CronJob


def _make_job(command: str = "echo ok > /dev/null 2>&1") -> CronJob:
    return CronJob(
        minute="0", hour="*", dom="*", month="*", dow="*",
        command=command, special=None, raw="",
    )


def _success(host: str, jobs):
    return AuditResult(host=host, success=True, jobs=jobs, error=None, raw_crontab="")


def _failure(host: str):
    return AuditResult(host=host, success=False, jobs=[], error="SSH error", raw_crontab="")


def test_run_lint_returns_results_for_successful_hosts():
    results = [_success("web1", [_make_job()]), _failure("db1")]
    report = run_lint(results)
    assert "web1" in report
    assert len(report["web1"]) == 1
    assert report["db1"] == []


def test_run_lint_empty_jobs_on_failure():
    report = run_lint([_failure("host1")])
    assert report["host1"] == []


def test_has_any_errors_true():
    results = [_success("h1", [_make_job(command="rm -rf / > /dev/null 2>&1")])]
    report = run_lint(results)
    assert has_any_errors(report) is True


def test_has_any_errors_false():
    results = [_success("h1", [_make_job()])]
    report = run_lint(results)
    assert has_any_errors(report) is False


def test_has_any_warnings_true():
    results = [_success("h1", [_make_job(command="/bin/task")])]
    report = run_lint(results)
    assert has_any_warnings(report) is True


def test_print_lint_report_outputs_host(capsys):
    results = [_success("web1", [_make_job(command="/bin/task")])]
    report = run_lint(results)
    print_lint_report(report)
    captured = capsys.readouterr()
    assert "web1" in captured.out
    assert "W001" in captured.out


def test_print_lint_report_errors_only_filters_warnings(capsys):
    results = [_success("web1", [_make_job(command="/bin/task")])]
    report = run_lint(results)
    print_lint_report(report, errors_only=True)
    captured = capsys.readouterr()
    assert "W001" not in captured.out
