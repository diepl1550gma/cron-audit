"""Tests for cron_audit.tagger and cron_audit.tag_config."""

from __future__ import annotations

import pytest

from cron_audit.parser import CronJob
from cron_audit.tag_config import load_tag_rules_from_dict
from cron_audit.tagger import (
    TagRule,
    TaggedJob,
    TaggingReport,
    build_tagging_report,
    format_tagging_report,
    tag_job,
    tag_jobs,
)


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


BACKUP_RULE = TagRule(pattern=r"backup", tags=["backup"])
DB_RULE = TagRule(pattern=r"(mysql|psql|pg_dump)", tags=["database", "backup"])
CLEAN_RULE = TagRule(pattern=r"rm\s+-rf", tags=["destructive"])


def test_tag_rule_matches_case_insensitive():
    rule = TagRule(pattern=r"backup", tags=["backup"])
    assert rule.matches("run_BACKUP_script.sh")
    assert not rule.matches("deploy.sh")


def test_tag_job_no_match_returns_empty_tags():
    job = _make_job("/usr/bin/deploy.sh")
    result = tag_job(job, [BACKUP_RULE, DB_RULE])
    assert isinstance(result, TaggedJob)
    assert result.tags == []
    assert not result.has_tags


def test_tag_job_single_rule_match():
    job = _make_job("/scripts/backup_db.sh")
    result = tag_job(job, [BACKUP_RULE, CLEAN_RULE])
    assert result.tags == ["backup"]
    assert result.has_tags


def test_tag_job_multiple_rules_deduplicated():
    job = _make_job("/usr/bin/pg_dump mydb")
    result = tag_job(job, [BACKUP_RULE, DB_RULE])
    # DB_RULE adds 'database' and 'backup'; BACKUP_RULE also adds 'backup' — no duplicate
    assert "database" in result.tags
    assert result.tags.count("backup") == 1


def test_tag_jobs_returns_one_per_job():
    jobs = [_make_job("/backup.sh"), _make_job("/deploy.sh"), _make_job("pg_dump prod")]
    results = tag_jobs(jobs, [BACKUP_RULE, DB_RULE])
    assert len(results) == 3
    assert results[0].has_tags
    assert not results[1].has_tags
    assert results[2].has_tags


def test_build_tagging_report_counts():
    jobs = [_make_job("/backup.sh"), _make_job("/deploy.sh")]
    report = build_tagging_report("web01", jobs, [BACKUP_RULE])
    assert report.host == "web01"
    assert report.tagged_count == 1
    assert report.untagged_count == 1


def test_format_tagging_report_contains_host():
    jobs = [_make_job("/backup.sh")]
    report = build_tagging_report("db01", jobs, [BACKUP_RULE])
    output = format_tagging_report(report)
    assert "db01" in output
    assert "backup" in output
    assert "Summary" in output


def test_format_tagging_report_untagged_label():
    jobs = [_make_job("/deploy.sh")]
    report = build_tagging_report("db01", jobs, [BACKUP_RULE])
    output = format_tagging_report(report)
    assert "(untagged)" in output


def test_load_tag_rules_from_dict():
    data = {
        "rules": [
            {"pattern": "backup", "tags": ["backup"]},
            {"pattern": "rm -rf", "tags": ["destructive"]},
        ]
    }
    rules = load_tag_rules_from_dict(data)
    assert len(rules) == 2
    assert rules[0].tags == ["backup"]
    assert rules[1].tags == ["destructive"]


def test_load_tag_rules_from_dict_missing_pattern_raises():
    with pytest.raises(ValueError, match="pattern"):
        load_tag_rules_from_dict({"rules": [{"tags": ["backup"]}]})


def test_load_tag_rules_from_dict_missing_tags_raises():
    with pytest.raises(ValueError, match="no tags"):
        load_tag_rules_from_dict({"rules": [{"pattern": "backup", "tags": []}]})
