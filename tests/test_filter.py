"""Tests for cron_audit.filter module."""

from __future__ import annotations

import pytest

from cron_audit.parser import CronJob
from cron_audit.filter import FilterCriteria, filter_jobs, format_filter_summary


def _make_job(
    command: str = "/usr/bin/backup.sh",
    minute: str = "0",
    hour: str = "2",
    dom: str = "*",
    month: str = "*",
    dow: str = "*",
    special: str = "",
) -> CronJob:
    return CronJob(
        minute=minute,
        hour=hour,
        dom=dom,
        month=month,
        dow=dow,
        command=command,
        special=special,
        raw="",
    )


def test_no_criteria_returns_all():
    jobs = [_make_job("/bin/foo"), _make_job("/bin/bar")]
    result = filter_jobs(jobs, FilterCriteria())
    assert result == jobs


def test_command_pattern_matches_substring():
    jobs = [_make_job("/usr/bin/backup.sh"), _make_job("/bin/cleanup.sh")]
    result = filter_jobs(jobs, FilterCriteria(command_pattern="backup"))
    assert len(result) == 1
    assert result[0].command == "/usr/bin/backup.sh"


def test_command_pattern_regex():
    jobs = [_make_job("/bin/foo"), _make_job("/bin/bar"), _make_job("/usr/local/baz")]
    result = filter_jobs(jobs, FilterCriteria(command_pattern=r"/bin/(foo|bar)"))
    assert len(result) == 2


def test_special_string_filter():
    jobs = [
        _make_job(special="@daily"),
        _make_job(special="@hourly"),
        _make_job(),
    ]
    result = filter_jobs(jobs, FilterCriteria(special_string="@daily"))
    assert len(result) == 1
    assert result[0].special == "@daily"


def test_max_runs_per_day_filters_high_frequency():
    # every minute = ~1440 runs/day; every hour = ~24 runs/day
    every_minute = _make_job(minute="*", hour="*", command="/bin/noisy")
    every_hour = _make_job(minute="0", hour="*", command="/bin/hourly")
    result = filter_jobs(
        [every_minute, every_hour],
        FilterCriteria(max_runs_per_day=100),
    )
    assert every_minute not in result
    assert every_hour in result


def test_min_runs_per_day_filters_low_frequency():
    daily = _make_job(minute="0", hour="2", command="/bin/daily")
    every_minute = _make_job(minute="*", hour="*", command="/bin/noisy")
    result = filter_jobs(
        [daily, every_minute],
        FilterCriteria(min_runs_per_day=100),
    )
    assert daily not in result
    assert every_minute in result


def test_empty_jobs_returns_empty():
    result = filter_jobs([], FilterCriteria(command_pattern="anything"))
    assert result == []


def test_format_filter_summary_no_matches():
    summary = format_filter_summary([], FilterCriteria())
    assert "0 job(s)" in summary
    assert "no jobs matched" in summary


def test_format_filter_summary_with_jobs():
    jobs = [_make_job("/bin/backup.sh")]
    summary = format_filter_summary(jobs, FilterCriteria())
    assert "1 job(s)" in summary
    assert "/bin/backup.sh" in summary
