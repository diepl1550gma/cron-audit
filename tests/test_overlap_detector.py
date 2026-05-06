"""Tests for cron_audit.overlap_detector."""
from __future__ import annotations

from cron_audit.parser import CronJob
from cron_audit.remote_audit import AuditResult
from cron_audit.overlap_detector import (
    OverlapReport,
    detect_overlaps,
    format_overlap_report,
)


def _job(
    command: str,
    minute: str = "0",
    hour: str = "*",
    dom: str = "*",
    month: str = "*",
    dow: str = "*",
    special: str | None = None,
) -> CronJob:
    return CronJob(
        minute=minute,
        hour=hour,
        day_of_month=dom,
        month=month,
        day_of_week=dow,
        command=command,
        special=special,
        raw=command,
    )


def _success(host: str, jobs: list) -> AuditResult:
    return AuditResult(host=host, success=True, jobs=jobs, error=None)


def _failure(host: str) -> AuditResult:
    return AuditResult(host=host, success=False, jobs=[], error="SSH error")


def test_no_overlaps_returns_empty_hints():
    jobs = [
        _job("/usr/bin/backup.sh", minute="0", hour="2"),
        _job("/usr/bin/cleanup.sh", minute="30", hour="3"),
    ]
    result = _success("host1", jobs)
    report = detect_overlaps(result)
    assert not report.has_overlaps()
    assert report.hints == []


def test_identical_schedule_triggers_overlap():
    jobs = [
        _job("/usr/bin/job_a.sh", minute="0", hour="4"),
        _job("/usr/bin/job_b.sh", minute="0", hour="4"),
    ]
    result = _success("host1", jobs)
    report = detect_overlaps(result)
    assert report.has_overlaps()
    assert len(report.hints) == 1
    assert "0 4 * * *" in report.hints[0].reason


def test_special_string_overlap_detected():
    jobs = [
        _job("/usr/bin/daily_a.sh", special="@daily"),
        _job("/usr/bin/daily_b.sh", special="@daily"),
    ]
    result = _success("host2", jobs)
    report = detect_overlaps(result)
    assert report.has_overlaps()
    assert report.hints[0].reason == "Identical schedule '@daily'"


def test_failed_host_returns_empty_report():
    result = _failure("host3")
    report = detect_overlaps(result)
    assert not report.has_overlaps()
    assert report.host == "host3"


def test_three_jobs_same_schedule_two_pairs():
    jobs = [
        _job("/bin/a", minute="15", hour="6"),
        _job("/bin/b", minute="15", hour="6"),
        _job("/bin/c", minute="15", hour="6"),
    ]
    result = _success("host4", jobs)
    report = detect_overlaps(result)
    # pairs: (0,1), (0,2), (1,2) -> 3 hints
    assert len(report.hints) == 3


def test_format_overlap_report_no_overlaps():
    report = OverlapReport(host="clean-host", hints=[])
    output = format_overlap_report(report)
    assert "clean-host" in output
    assert "No scheduling overlaps" in output


def test_format_overlap_report_with_overlaps():
    jobs = [
        _job("/bin/foo", minute="0", hour="1"),
        _job("/bin/bar", minute="0", hour="1"),
    ]
    result = _success("host5", jobs)
    report = detect_overlaps(result)
    output = format_overlap_report(report)
    assert "[OVERLAP]" in output
    assert "/bin/foo" in output
    assert "/bin/bar" in output
