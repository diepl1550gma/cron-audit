"""Lint cron jobs for common issues and anti-patterns."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List

from cron_audit.parser import CronJob


@dataclass
class LintIssue:
    severity: str  # "error" | "warning" | "info"
    code: str
    message: str


@dataclass
class LintResult:
    job: CronJob
    issues: List[LintIssue] = field(default_factory=list)

    @property
    def has_errors(self) -> bool:
        return any(i.severity == "error" for i in self.issues)

    @property
    def has_warnings(self) -> bool:
        return any(i.severity == "warning" for i in self.issues)


_REDIRECT_SUPPRESSED = ("> /dev/null", ">/dev/null", "2>&1")
_MISSING_OUTPUT_REDIRECT = True


def _check_output_redirect(job: CronJob) -> List[LintIssue]:
    cmd = job.command
    if all(token not in cmd for token in _REDIRECT_SUPPRESSED):
        return [
            LintIssue(
                severity="warning",
                code="W001",
                message="Command does not redirect output; cron may send mail on every run.",
            )
        ]
    return []


def _check_root_command(job: CronJob) -> List[LintIssue]:
    dangerous = ("rm -rf /", "mkfs", "dd if=", "> /dev/sda")
    for pat in dangerous:
        if pat in job.command:
            return [
                LintIssue(
                    severity="error",
                    code="E001",
                    message=f"Potentially destructive pattern detected: '{pat}'.",
                )
            ]
    return []


def _check_no_command(job: CronJob) -> List[LintIssue]:
    if not job.command or not job.command.strip():
        return [
            LintIssue(severity="error", code="E002", message="Cron job has an empty command.")
        ]
    return []


def _check_special_string(job: CronJob) -> List[LintIssue]:
    if job.special and job.special == "@reboot":
        return [
            LintIssue(
                severity="info",
                code="I001",
                message="@reboot jobs run once on startup; ensure idempotency.",
            )
        ]
    return []


_CHECKS = [_check_no_command, _check_root_command, _check_output_redirect, _check_special_string]


def lint_job(job: CronJob) -> LintResult:
    issues: List[LintIssue] = []
    for check in _CHECKS:
        issues.extend(check(job))
    return LintResult(job=job, issues=issues)


def lint_jobs(jobs: List[CronJob]) -> List[LintResult]:
    return [lint_job(j) for j in jobs]
