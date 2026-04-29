"""Tests for cron_audit.snapshot_cli."""

from __future__ import annotations

import json
import os
from unittest.mock import patch

import pytest

from cron_audit.parser import CronJob
from cron_audit.remote_audit import AuditResult
from cron_audit.snapshot_cli import (
    diff_against_snapshots,
    has_any_changes,
    print_diff_reports,
    snapshot_hosts,
)


def _make_job(command: str = "/usr/bin/backup") -> CronJob:
    return CronJob(
        minute="0",
        hour="2",
        day_of_month="*",
        month="*",
        day_of_week="*",
        command=command,
        raw=f"0 2 * * * {command}",
    )


def _success(host: str, jobs=None) -> AuditResult:
    return AuditResult(host=host, success=True, jobs=jobs or [_make_job()], error=None)


def _failure(host: str) -> AuditResult:
    return AuditResult(host=host, success=False, jobs=None, error="timeout")


# ---------------------------------------------------------------------------
# snapshot_hosts
# ---------------------------------------------------------------------------

def test_snapshot_hosts_writes_file(tmp_path):
    results = [_success("web1")]
    written = snapshot_hosts(results, str(tmp_path))
    assert len(written) == 1
    assert os.path.exists(written[0])
    with open(written[0]) as fh:
        data = json.load(fh)
    assert data["host"] == "web1"


def test_snapshot_hosts_skips_failures(tmp_path):
    results = [_failure("db1")]
    written = snapshot_hosts(results, str(tmp_path))
    assert written == []


def test_snapshot_hosts_creates_dir(tmp_path):
    target = str(tmp_path / "new" / "subdir")
    snapshot_hosts([_success("web1")], target)
    assert os.path.isdir(target)


# ---------------------------------------------------------------------------
# diff_against_snapshots
# ---------------------------------------------------------------------------

def test_diff_no_snapshot_skipped(tmp_path):
    results = [_success("web1")]
    diffs = diff_against_snapshots(results, str(tmp_path))
    assert diffs == []


def test_diff_detects_added_job(tmp_path):
    old_jobs = [_make_job("/bin/old")]
    snapshot_hosts(
        [AuditResult(host="web1", success=True, jobs=old_jobs, error=None)],
        str(tmp_path),
    )
    new_jobs = [_make_job("/bin/old"), _make_job("/bin/new")]
    results = [AuditResult(host="web1", success=True, jobs=new_jobs, error=None)]
    diffs = diff_against_snapshots(results, str(tmp_path))
    assert len(diffs) == 1
    assert len(diffs[0].added) == 1


def test_diff_skips_failed_results(tmp_path):
    snapshot_hosts([_success("web1")], str(tmp_path))
    diffs = diff_against_snapshots([_failure("web1")], str(tmp_path))
    assert diffs == []


# ---------------------------------------------------------------------------
# has_any_changes / print_diff_reports
# ---------------------------------------------------------------------------

def test_has_any_changes_true(tmp_path):
    snapshot_hosts(
        [AuditResult(host="web1", success=True, jobs=[], error=None)],
        str(tmp_path),
    )
    results = [_success("web1")]
    diffs = diff_against_snapshots(results, str(tmp_path))
    assert has_any_changes(diffs) is True


def test_print_diff_reports_only_changes(tmp_path, capsys):
    snapshot_hosts([_success("web1")], str(tmp_path))
    results = [_success("web1")]
    diffs = diff_against_snapshots(results, str(tmp_path))
    print_diff_reports(diffs, only_changes=True)
    captured = capsys.readouterr()
    assert captured.out == ""
