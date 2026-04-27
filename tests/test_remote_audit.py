"""Tests for remote_audit orchestration logic using mocked SSH calls."""

from unittest.mock import MagicMock, patch

import pytest

from cron_audit.remote_audit import (
    AuditResult,
    audit_host,
    audit_hosts,
    format_audit_report,
)
from cron_audit.ssh_client import RemoteCrontab, SSHConfig

SAMPLE_CRONTAB_LINES = [
    "# Daily backup",
    "0 2 * * * /usr/local/bin/backup.sh",
    "*/15 * * * * /usr/bin/check_health.py",
    "",
]


def _make_config(hostname="web01", username="deploy") -> SSHConfig:
    return SSHConfig(hostname=hostname, username=username)


@patch("cron_audit.remote_audit.fetch_crontab")
def test_audit_host_success(mock_fetch):
    mock_fetch.return_value = RemoteCrontab(
        hostname="web01", username="deploy", raw_lines=SAMPLE_CRONTAB_LINES
    )
    result = audit_host(_make_config())
    assert result.success
    assert result.hostname == "web01"
    assert result.summary["total_jobs"] == 2


@patch("cron_audit.remote_audit.fetch_crontab")
def test_audit_host_ssh_failure(mock_fetch):
    mock_fetch.return_value = RemoteCrontab(
        hostname="web01", username="deploy", error="Connection refused"
    )
    result = audit_host(_make_config())
    assert not result.success
    assert result.error == "Connection refused"
    assert result.summary == {}


@patch("cron_audit.remote_audit.fetch_crontab")
def test_audit_hosts_multiple(mock_fetch):
    mock_fetch.return_value = RemoteCrontab(
        hostname="any", username="deploy", raw_lines=SAMPLE_CRONTAB_LINES
    )
    configs = [_make_config("host1"), _make_config("host2")]
    results = audit_hosts(configs)
    assert len(results) == 2
    assert mock_fetch.call_count == 2


@patch("cron_audit.remote_audit.fetch_crontab")
def test_format_audit_report_success(mock_fetch):
    mock_fetch.return_value = RemoteCrontab(
        hostname="web01", username="deploy", raw_lines=SAMPLE_CRONTAB_LINES
    )
    result = audit_host(_make_config())
    report = format_audit_report([result])
    assert "deploy@web01" in report
    assert "Total jobs" in report
    assert "backup.sh" in report


@patch("cron_audit.remote_audit.fetch_crontab")
def test_format_audit_report_error(mock_fetch):
    mock_fetch.return_value = RemoteCrontab(
        hostname="db01", username="root", error="Timeout"
    )
    result = audit_host(_make_config("db01", "root"))
    report = format_audit_report([result])
    assert "ERROR" in report
    assert "Timeout" in report


def test_audit_result_success_flag():
    ok = AuditResult(hostname="h", username="u", summary={"total_jobs": 1})
    assert ok.success
    err = AuditResult(hostname="h", username="u", error="oops")
    assert not err.success
