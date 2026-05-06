"""Risk scoring for cron jobs based on command patterns, schedule frequency, and output handling."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List

from cron_audit.parser import CronJob
from cron_audit.scheduler import describe_schedule

_HIGH_RISK_PATTERNS = [
    "rm ", "rm -", "drop ", "truncate ", "mkfs", "dd if",
    "chmod 777", "curl", "wget", "bash -c", "sh -c", "eval",
    ">/dev/null 2>&1",  # silences all output — masks failures
]

_MEDIUM_RISK_PATTERNS = [
    "sudo", "mysqldump", "pg_dump", "rsync", "scp", "ssh",
    "python", "ruby", "node", "php",
]

MAX_SCORE = 100


@dataclass
class RiskScore:
    job: CronJob
    score: int  # 0–100
    level: str  # "low", "medium", "high", "critical"
    reasons: List[str] = field(default_factory=list)


def _score_command(command: str) -> tuple[int, List[str]]:
    reasons: List[str] = []
    score = 0
    cmd_lower = command.lower()

    for pattern in _HIGH_RISK_PATTERNS:
        if pattern in cmd_lower:
            score += 25
            reasons.append(f"High-risk pattern detected: '{pattern}'")

    for pattern in _MEDIUM_RISK_PATTERNS:
        if pattern in cmd_lower:
            score += 10
            reasons.append(f"Medium-risk pattern detected: '{pattern}'")

    if "2>&1" not in command and ">" not in command:
        score += 5
        reasons.append("No output redirection — failures may go unnoticed")

    return score, reasons


def _score_frequency(job: CronJob) -> tuple[int, List[str]]:
    reasons: List[str] = []
    score = 0
    try:
        summary = describe_schedule(job)
        rpd = summary.estimated_runs_per_day
        if rpd >= 60:
            score += 20
            reasons.append(f"Very high frequency: ~{rpd} runs/day")
        elif rpd >= 24:
            score += 10
            reasons.append(f"High frequency: ~{rpd} runs/day")
        elif rpd >= 6:
            score += 5
            reasons.append(f"Moderate frequency: ~{rpd} runs/day")
    except Exception:
        pass
    return score, reasons


def score_job(job: CronJob) -> RiskScore:
    """Compute a risk score for a single cron job."""
    total = 0
    all_reasons: List[str] = []

    cmd_score, cmd_reasons = _score_command(job.command)
    freq_score, freq_reasons = _score_frequency(job)

    total = min(cmd_score + freq_score, MAX_SCORE)
    all_reasons = cmd_reasons + freq_reasons

    if total >= 70:
        level = "critical"
    elif total >= 45:
        level = "high"
    elif total >= 20:
        level = "medium"
    else:
        level = "low"

    return RiskScore(job=job, score=total, level=level, reasons=all_reasons)


def score_jobs(jobs: List[CronJob]) -> List[RiskScore]:
    """Score a list of cron jobs, sorted by descending risk score."""
    return sorted([score_job(j) for j in jobs], key=lambda r: r.score, reverse=True)
