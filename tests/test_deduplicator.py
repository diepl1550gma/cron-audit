"""Tests for cron_audit.deduplicator."""

from __future__ import annotations

import pytest

from cron_audit.parser import CronJob
from cron_audit.remote_audit import AuditResult
from cron_audit.deduplicator import (
    find_duplicates_in_host,
    find_duplicates_across_hosts,
    format_dedup_report,
)


def _job(minute="0", hour="*", dom="*", month="*", dow="*", command="/bin/task",
         special=None) -> CronJob:
    return CronJob(
        minute=minute, hour=hour, day_of_month=dom,
        month=month, day_of_week=dow, command=command,
        special=special, raw_line=command,
    )


def _success(host: str, jobs) -> AuditResult:
    return AuditResult(host=host, success=True, jobs=jobs, error=None)


def _failure(host: str) -> AuditResult:
    return AuditResult(host=host, success=False, jobs=None, error="ssh error")


# ── single-host deduplication ──────────────────────────────────────────────

def test_no_duplicates_within_host():
    jobs = [_job(command="/bin/a"), _job(command="/bin/b")]
    report = find_duplicates_in_host("web1", jobs)
    assert not report.has_duplicates
    assert report.duplicate_groups == []


def test_duplicate_detected_within_host():
    job = _job(command="/bin/backup")
    report = find_duplicates_in_host("web1", [job, job])
    assert report.has_duplicates
    assert len(report.duplicate_groups) == 1
    assert report.duplicate_groups[0].count == 2
    assert report.duplicate_groups[0].command == "/bin/backup"


def test_multiple_duplicate_groups_within_host():
    jobs = [
        _job(command="/bin/a"), _job(command="/bin/a"),
        _job(command="/bin/b", hour="2"), _job(command="/bin/b", hour="2"),
    ]
    report = find_duplicates_in_host("web1", jobs)
    assert len(report.duplicate_groups) == 2


def test_special_string_duplicates():
    job = _job(special="@daily", command="/bin/daily")
    report = find_duplicates_in_host("db1", [job, job])
    assert report.has_duplicates
    assert report.duplicate_groups[0].schedule == "@daily"


# ── cross-host deduplication ───────────────────────────────────────────────

def test_no_cross_host_duplicates():
    r1 = _success("host1", [_job(command="/bin/a")])
    r2 = _success("host2", [_job(command="/bin/b")])
    report = find_duplicates_across_hosts([r1, r2])
    assert not report.has_duplicates


def test_cross_host_duplicate_detected():
    shared = _job(command="/bin/shared")
    r1 = _success("host1", [shared])
    r2 = _success("host2", [shared])
    report = find_duplicates_across_hosts([r1, r2])
    assert report.has_duplicates
    hosts = [h for h, _ in report.duplicate_groups[0].occurrences]
    assert "host1" in hosts and "host2" in hosts


def test_failed_host_skipped_in_cross_host():
    shared = _job(command="/bin/shared")
    r1 = _success("host1", [shared])
    r2 = _failure("host2")
    report = find_duplicates_across_hosts([r1, r2])
    assert not report.has_duplicates


# ── formatting ─────────────────────────────────────────────────────────────

def test_format_no_duplicates():
    jobs = [_job(command="/bin/unique")]
    report = find_duplicates_in_host("web1", jobs)
    output = format_dedup_report(report)
    assert "No duplicates found" in output


def test_format_with_duplicates():
    job = _job(command="/bin/backup")
    report = find_duplicates_in_host("web1", [job, job])
    output = format_dedup_report(report)
    assert "/bin/backup" in output
    assert "Count    : 2" in output
    assert "web1" in output
