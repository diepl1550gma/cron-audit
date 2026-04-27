"""Tests for cron_audit.exporter."""

from __future__ import annotations

import json

import pytest

from cron_audit.parser import CronJob
from cron_audit.remote_audit import AuditResult
from cron_audit.exporter import export_json, export_csv, export_markdown


def _make_job(command: str = "/usr/bin/backup") -> CronJob:
    return CronJob(
        raw=f"0 2 * * 0 {command}",
        minute="0",
        hour="2",
        day_of_month="*",
        month="*",
        day_of_week="0",
        command=command,
        special=None,
    )


def _make_success(host: str = "web01") -> AuditResult:
    return AuditResult(host=host, success=True, jobs=[_make_job()], error=None)


def _make_failure(host: str = "db01") -> AuditResult:
    return AuditResult(host=host, success=False, jobs=[], error="Connection refused")


# --- JSON ---

def test_export_json_success():
    result = export_json([_make_success()])
    data = json.loads(result)
    assert len(data) == 1
    assert data[0]["host"] == "web01"
    assert data[0]["success"] is True
    assert len(data[0]["jobs"]) == 1
    assert data[0]["jobs"][0]["command"] == "/usr/bin/backup"


def test_export_json_failure():
    result = export_json([_make_failure()])
    data = json.loads(result)
    assert data[0]["success"] is False
    assert data[0]["error"] == "Connection refused"
    assert data[0]["jobs"] == []


def test_export_json_multiple_hosts():
    result = export_json([_make_success("h1"), _make_failure("h2")])
    data = json.loads(result)
    assert len(data) == 2


# --- CSV ---

def test_export_csv_contains_header():
    result = export_csv([_make_success()])
    assert "host" in result
    assert "command" in result


def test_export_csv_success_row():
    result = export_csv([_make_success()])
    assert "web01" in result
    assert "/usr/bin/backup" in result


def test_export_csv_failure_row():
    result = export_csv([_make_failure()])
    assert "db01" in result
    assert "Connection refused" in result


# --- Markdown ---

def test_export_markdown_contains_host():
    result = export_markdown([_make_success()])
    assert "## Host: web01" in result


def test_export_markdown_contains_table_header():
    result = export_markdown([_make_success()])
    assert "| Minute |" in result
    assert "| Command |" in result


def test_export_markdown_failure_shows_error():
    result = export_markdown([_make_failure()])
    assert "**Error:**" in result
    assert "Connection refused" in result


def test_export_markdown_no_jobs():
    r = AuditResult(host="empty", success=True, jobs=[], error=None)
    result = export_markdown([r])
    assert "No cron jobs found" in result
