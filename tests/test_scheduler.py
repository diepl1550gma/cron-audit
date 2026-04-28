"""Tests for cron_audit.scheduler."""

import pytest

from cron_audit.parser import CronJob
from cron_audit.scheduler import ScheduleSummary, describe_schedule


def _make_job(schedule: str, command: str = "echo hi") -> CronJob:
    return CronJob(
        raw_line=f"{schedule} {command}",
        raw_schedule=schedule,
        command=command,
        minute=schedule.split()[0] if not schedule.startswith("@") else None,
        hour=schedule.split()[1] if not schedule.startswith("@") else None,
        dom=schedule.split()[2] if not schedule.startswith("@") else None,
        month=schedule.split()[3] if not schedule.startswith("@") else None,
        dow=schedule.split()[4] if not schedule.startswith("@") else None,
    )


class TestDescribeSchedule:
    def test_special_reboot(self):
        job = _make_job("@reboot")
        summary = describe_schedule(job)
        assert summary.is_special is True
        assert summary.description == "At system reboot"
        assert summary.estimated_runs_per_day is None

    def test_special_daily(self):
        job = _make_job("@daily")
        summary = describe_schedule(job)
        assert summary.is_special is True
        assert "midnight" in summary.description.lower()

    def test_special_hourly(self):
        job = _make_job("@hourly")
        summary = describe_schedule(job)
        assert summary.is_special is True
        assert summary.estimated_runs_per_day is None

    def test_every_minute(self):
        job = _make_job("* * * * *")
        summary = describe_schedule(job)
        assert summary.is_special is False
        assert "every minute" in summary.description
        assert summary.estimated_runs_per_day == pytest.approx(1440.0)

    def test_every_hour_at_minute_30(self):
        job = _make_job("30 * * * *")
        summary = describe_schedule(job)
        assert "every hour" in summary.description
        assert "30" in summary.description
        assert summary.estimated_runs_per_day == pytest.approx(24.0)

    def test_specific_hour(self):
        job = _make_job("0 6 * * *")
        summary = describe_schedule(job)
        assert "6:00" in summary.description
        assert summary.estimated_runs_per_day == pytest.approx(1.0)

    def test_with_dom_restriction(self):
        job = _make_job("0 0 1 * *")
        summary = describe_schedule(job)
        assert "day-of-month 1" in summary.description

    def test_with_month_restriction(self):
        job = _make_job("0 0 * 6 *")
        summary = describe_schedule(job)
        assert "month 6" in summary.description

    def test_with_dow_restriction(self):
        job = _make_job("0 9 * * 1")
        summary = describe_schedule(job)
        assert "weekday 1" in summary.description

    def test_step_in_hour(self):
        job = _make_job("0 */6 * * *")
        summary = describe_schedule(job)
        assert summary.estimated_runs_per_day == pytest.approx(4.0)

    def test_comma_list_in_minute(self):
        job = _make_job("0,15,30,45 * * * *")
        summary = describe_schedule(job)
        # 4 minutes * 24 hours = 96
        assert summary.estimated_runs_per_day == pytest.approx(96.0)

    def test_raw_preserved(self):
        raw = "5 4 * * 0"
        job = _make_job(raw)
        summary = describe_schedule(job)
        assert summary.raw == raw

    def test_invalid_format_returns_unknown(self):
        job = CronJob(
            raw_line="bad_schedule cmd",
            raw_schedule="bad_schedule",
            command="cmd",
            minute=None,
            hour=None,
            dom=None,
            month=None,
            dow=None,
        )
        summary = describe_schedule(job)
        assert "Unknown" in summary.description
        assert summary.estimated_runs_per_day is None
