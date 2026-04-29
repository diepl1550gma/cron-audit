"""Tests for cron_audit.tag_cli."""

from __future__ import annotations

from typing import List, Optional

from cron_audit.parser import CronJob
from cron_audit.remote_audit import AuditResult
from cron_audit.tag_cli import has_any_untagged, jobs_by_tag, run_tagging
from cron_audit.tagger import TagRule


def _make_job(command: str) -> CronJob:
    return CronJob(
        minute="0",
        hour="*",
        day_of_month="*",
        month="*",
        day_of_week="*",
        command=command,
        raw=f"0 * * * * {command}",
        special=None,
    )


def _success(host: str, jobs: List[CronJob]) -> AuditResult:
    return AuditResult(host=host, success=True, jobs=jobs, error=None)


def _failure(host: str) -> AuditResult:
    return AuditResult(host=host, success=False, jobs=None, error="SSH error")


BACKUP_RULE = TagRule(pattern=r"backup", tags=["backup"])


def test_run_tagging_skips_failures():
    results = [_failure("bad-host"), _success("ok-host", [_make_job("/backup.sh")])]
    reports = run_tagging(results, [BACKUP_RULE])
    assert len(reports) == 1
    assert reports[0].host == "ok-host"


def test_run_tagging_returns_report_per_success():
    results = [
        _success("host1", [_make_job("/backup.sh"), _make_job("/deploy.sh")]),
        _success("host2", [_make_job("/cleanup.sh")]),
    ]
    reports = run_tagging(results, [BACKUP_RULE])
    assert len(reports) == 2


def test_has_any_untagged_true():
    results = [_success("h1", [_make_job("/deploy.sh")])]
    reports = run_tagging(results, [BACKUP_RULE])
    assert has_any_untagged(reports) is True


def test_has_any_untagged_false_when_all_tagged():
    results = [_success("h1", [_make_job("/backup.sh")])]
    reports = run_tagging(results, [BACKUP_RULE])
    assert has_any_untagged(reports) is False


def test_has_any_untagged_false_empty_reports():
    assert has_any_untagged([]) is False


def test_jobs_by_tag_returns_matching_commands():
    results = [
        _success("h1", [_make_job("/backup.sh"), _make_job("/deploy.sh")]),
        _success("h2", [_make_job("/run_backup.py")]),
    ]
    reports = run_tagging(results, [BACKUP_RULE])
    tagged = jobs_by_tag(reports, "backup")
    assert len(tagged) == 2
    assert any("h1" in entry for entry in tagged)
    assert any("h2" in entry for entry in tagged)


def test_jobs_by_tag_empty_when_no_match():
    results = [_success("h1", [_make_job("/deploy.sh")])]
    reports = run_tagging(results, [BACKUP_RULE])
    tagged = jobs_by_tag(reports, "backup")
    assert tagged == []
