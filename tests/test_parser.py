"""Tests for cron_audit.parser and cron_audit.crontab_reader."""

import pytest
from cron_audit.parser import parse_cron_line, CronJob
from cron_audit.crontab_reader import parse_crontab, summarize_jobs


class TestParseCronLine:
    def test_blank_line_returns_none(self):
        assert parse_cron_line("") is None

    def test_comment_returns_none(self):
        assert parse_cron_line("# this is a comment") is None

    def test_valid_standard_cron(self):
        job = parse_cron_line("0 5 * * 1 /usr/bin/backup.sh")
        assert job is not None
        assert job.is_valid
        assert job.schedule == "0 5 * * 1"
        assert job.command == "/usr/bin/backup.sh"

    def test_valid_special_string(self):
        job = parse_cron_line("@daily /usr/bin/cleanup")
        assert job is not None
        assert job.is_valid
        assert job.schedule == "@daily"
        assert job.command == "/usr/bin/cleanup"

    def test_invalid_minute_field(self):
        job = parse_cron_line("99 5 * * 1 /usr/bin/backup.sh")
        assert job is not None
        assert not job.is_valid
        assert "minute" in job.error

    def test_invalid_hour_field(self):
        job = parse_cron_line("0 25 * * 1 /usr/bin/backup.sh")
        assert not job.is_valid
        assert "hour" in job.error

    def test_too_few_fields(self):
        job = parse_cron_line("0 5 * *")
        assert not job.is_valid
        assert "Insufficient" in job.error

    def test_step_syntax(self):
        job = parse_cron_line("*/15 * * * * /check.sh")
        assert job.is_valid

    def test_range_syntax(self):
        job = parse_cron_line("0 8-17 * * 1-5 /work.sh")
        assert job.is_valid

    def test_list_syntax(self):
        job = parse_cron_line("0 6,12,18 * * * /notify.sh")
        assert job.is_valid

    def test_user_not_set_by_default(self):
        job = parse_cron_line("0 0 * * * /bin/true")
        assert job.user is None


class TestCrontabReader:
    SAMPLE_CRONTAB = """
# Daily backup
0 2 * * * /usr/bin/backup.sh

# Hourly check
*/30 * * * * /usr/bin/check.sh

# Bad line
99 99 * * * /bad.sh

@reboot /usr/bin/startup.sh
"""

    def test_parse_crontab_count(self):
        jobs = parse_crontab(self.SAMPLE_CRONTAB)
        assert len(jobs) == 4

    def test_parse_crontab_assigns_user(self):
        jobs = parse_crontab(self.SAMPLE_CRONTAB, user="root")
        assert all(j.user == "root" for j in jobs)

    def test_summarize_jobs(self):
        jobs = parse_crontab(self.SAMPLE_CRONTAB)
        summary = summarize_jobs(jobs)
        assert summary["total"] == 4
        assert summary["valid"] == 3
        assert summary["invalid"] == 1
        assert len(summary["errors"]) == 1
