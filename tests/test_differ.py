"""Tests for cron_audit.differ and cron_audit.snapshot."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from cron_audit.differ import CronDiff, diff_crontabs, format_diff_report
from cron_audit.parser import CronJob
from cron_audit.snapshot import load_snapshot, save_snapshot


def _job(schedule: str, command: str) -> CronJob:
    return CronJob(schedule=schedule, command=command, raw=f"{schedule} {command}")


# ---------------------------------------------------------------------------
# diff_crontabs
# ---------------------------------------------------------------------------

def test_no_changes_all_unchanged():
    jobs = [_job("0 * * * *", "echo hi"), _job("@daily", "/bin/backup")]
    diff = diff_crontabs("host1", jobs, jobs)
    assert not diff.has_changes
    assert len(diff.unchanged) == 2
    assert diff.added == []
    assert diff.removed == []


def test_added_job_detected():
    before = [_job("0 * * * *", "echo hi")]
    after = before + [_job("@daily", "/bin/backup")]
    diff = diff_crontabs("host1", before, after)
    assert diff.has_changes
    assert len(diff.added) == 1
    assert diff.added[0].command == "/bin/backup"
    assert diff.removed == []


def test_removed_job_detected():
    before = [_job("0 * * * *", "echo hi"), _job("@daily", "/bin/backup")]
    after = [_job("0 * * * *", "echo hi")]
    diff = diff_crontabs("host2", before, after)
    assert diff.has_changes
    assert len(diff.removed) == 1
    assert diff.removed[0].command == "/bin/backup"
    assert diff.added == []


def test_empty_before_all_added():
    after = [_job("*/5 * * * *", "ping localhost")]
    diff = diff_crontabs("host3", [], after)
    assert diff.has_changes
    assert len(diff.added) == 1
    assert diff.unchanged == []


# ---------------------------------------------------------------------------
# format_diff_report
# ---------------------------------------------------------------------------

def test_format_report_no_changes():
    diff = CronDiff(host="srv1", unchanged=[_job("@hourly", "echo ok")])
    report = format_diff_report([diff])
    assert "No changes detected" in report
    assert "srv1" in report


def test_format_report_shows_added_and_removed():
    diff = CronDiff(
        host="srv2",
        added=[_job("@reboot", "/start.sh")],
        removed=[_job("@daily", "/old.sh")],
    )
    report = format_diff_report([diff])
    assert "+ [@reboot] /start.sh" in report
    assert "- [@daily] /old.sh" in report


# ---------------------------------------------------------------------------
# save_snapshot / load_snapshot
# ---------------------------------------------------------------------------

def test_round_trip_snapshot(tmp_path: Path):
    snap = tmp_path / "snap.json"
    jobs = {"host1": [_job("@daily", "/bin/backup")], "host2": []}
    save_snapshot(snap, jobs)
    loaded = load_snapshot(snap)
    assert set(loaded.keys()) == {"host1", "host2"}
    assert loaded["host1"][0].command == "/bin/backup"
    assert loaded["host2"] == []


def test_load_snapshot_bad_version(tmp_path: Path):
    snap = tmp_path / "bad.json"
    snap.write_text(json.dumps({"version": 99, "hosts": {}}), encoding="utf-8")
    with pytest.raises(ValueError, match="Unsupported snapshot version"):
        load_snapshot(snap)


def test_load_snapshot_missing_file(tmp_path: Path):
    with pytest.raises(FileNotFoundError):
        load_snapshot(tmp_path / "nonexistent.json")
