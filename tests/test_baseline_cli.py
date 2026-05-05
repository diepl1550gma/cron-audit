"""Tests for cron_audit.baseline_cli."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from cron_audit.baseline_cli import (
    has_any_violations,
    print_baseline_reports,
    run_baseline_check,
)
from cron_audit.baseline import BaselineReport
from cron_audit.parser import CronJob
from cron_audit.remote_audit import AuditResult


def _job(command: str, schedule: str = "0 * * * *") -> CronJob:
    return CronJob(schedule=schedule, user=None, command=command, raw=f"{schedule} {command}")


def _success(host: str, jobs: list) -> AuditResult:
    return AuditResult(host=host, jobs=jobs, raw_crontab="", success=True, error=None)


def _failure(host: str) -> AuditResult:
    return AuditResult(host=host, jobs=[], raw_crontab="", success=False, error="err")


def test_run_baseline_check_returns_one_report_per_host(tmp_path: Path):
    baseline_file = tmp_path / "baseline.json"
    baseline_file.write_text(json.dumps({
        "web-01": [{"command": "/usr/bin/backup.sh", "schedule": "0 2 * * *"}]
    }))
    results = [
        _success("web-01", [_job("/usr/bin/backup.sh", "0 2 * * *")]),
        _success("db-01", []),
    ]
    reports = run_baseline_check(results, baseline_file)
    assert len(reports) == 2
    assert reports[0].host == "web-01"
    assert not reports[0].has_violations


def test_run_baseline_check_unknown_host_treated_as_empty(tmp_path: Path):
    baseline_file = tmp_path / "baseline.json"
    baseline_file.write_text(json.dumps({}))
    results = [_success("web-01", [_job("/usr/bin/mystery.sh")])]
    reports = run_baseline_check(results, baseline_file)
    assert reports[0].has_violations


def test_has_any_violations_true():
    from cron_audit.baseline import BaselineViolation
    job = _job("/bin/bad")
    v = BaselineViolation(host="h", job=job, reason="not in baseline")
    reports = [BaselineReport(host="h", violations=[v])]
    assert has_any_violations(reports) is True


def test_has_any_violations_false():
    reports = [BaselineReport(host="h")]
    assert has_any_violations(reports) is False


def test_print_baseline_reports_outputs_text(tmp_path: Path, capsys):
    baseline_file = tmp_path / "baseline.json"
    baseline_file.write_text(json.dumps({"web-01": []}))
    results = [_success("web-01", [])]
    reports = run_baseline_check(results, baseline_file)
    print_baseline_reports(reports)
    captured = capsys.readouterr()
    assert "web-01" in captured.out
