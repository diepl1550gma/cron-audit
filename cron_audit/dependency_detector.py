"""Detect potential ordering dependencies between cron jobs on the same host."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Sequence, Tuple

from cron_audit.parser import CronJob
from cron_audit.remote_audit import AuditResult


@dataclass
class DependencyHint:
    """A suspected dependency between two cron jobs."""
    job_a: CronJob
    job_b: CronJob
    reason: str


@dataclass
class DependencyReport:
    host: str
    hints: List[DependencyHint] = field(default_factory=list)


def has_dependencies(report: DependencyReport) -> bool:
    return bool(report.hints)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _extract_paths(command: str) -> List[str]:
    """Return tokens from a command that look like filesystem paths."""
    return [
        token.rstrip(";,|&>")
        for token in command.split()
        if token.startswith("/") and len(token) > 1
    ]


def _shared_path_hint(
    a: CronJob, b: CronJob
) -> DependencyHint | None:
    paths_a = set(_extract_paths(a.command))
    paths_b = set(_extract_paths(b.command))
    shared = paths_a & paths_b
    if shared:
        sample = sorted(shared)[0]
        return DependencyHint(
            job_a=a,
            job_b=b,
            reason=f"shared path reference: {sample}",
        )
    return None


def _extract_script_name(command: str) -> str | None:
    """Return the basename of the first executable-looking token."""
    for token in command.split():
        clean = token.lstrip("/").rstrip(";,|&")
        if clean and "." not in clean.split("/")[-1]:
            return clean.split("/")[-1]
    return None


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def detect_dependencies(jobs: Sequence[CronJob]) -> List[DependencyHint]:
    """Return dependency hints for a flat list of cron jobs."""
    hints: List[DependencyHint] = []
    job_list = list(jobs)
    for i, a in enumerate(job_list):
        for b in job_list[i + 1 :]:
            hint = _shared_path_hint(a, b)
            if hint:
                hints.append(hint)
    return hints


def build_dependency_reports(
    results: Sequence[AuditResult],
) -> List[DependencyReport]:
    """Build one DependencyReport per successful audit result."""
    reports: List[DependencyReport] = []
    for result in results:
        if not result.success or result.jobs is None:
            reports.append(DependencyReport(host=result.host))
            continue
        hints = detect_dependencies(result.jobs)
        reports.append(DependencyReport(host=result.host, hints=hints))
    return reports


def format_dependency_report(report: DependencyReport) -> str:
    lines = [f"=== Dependency hints for {report.host} ==="]
    if not report.hints:
        lines.append("  No dependency hints detected.")
    else:
        for h in report.hints:
            lines.append(f"  [{h.reason}]")
            lines.append(f"    A: {h.job_a.command}")
            lines.append(f"    B: {h.job_b.command}")
    return "\n".join(lines)
