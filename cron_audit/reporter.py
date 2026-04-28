"""Generate enriched audit reports with human-readable schedule descriptions."""

from __future__ import annotations

from dataclasses import dataclass
from typing import List

from cron_audit.parser import CronJob
from cron_audit.remote_audit import AuditResult
from cron_audit.scheduler import ScheduleSummary, describe_schedule


@dataclass
class EnrichedJob:
    """A CronJob paired with its schedule description."""

    job: CronJob
    schedule: ScheduleSummary


@dataclass
class EnrichedAuditResult:
    """AuditResult with schedule descriptions attached to each job."""

    host: str
    success: bool
    enriched_jobs: List[EnrichedJob]
    error: str | None = None


def enrich_audit_result(result: AuditResult) -> EnrichedAuditResult:
    """Attach schedule descriptions to every job in an AuditResult."""
    enriched: List[EnrichedJob] = [
        EnrichedJob(job=job, schedule=describe_schedule(job))
        for job in (result.jobs or [])
    ]
    return EnrichedAuditResult(
        host=result.host,
        success=result.success,
        enriched_jobs=enriched,
        error=result.error,
    )


def _format_enriched_job(ej: EnrichedJob) -> List[str]:
    """Render a single EnrichedJob as a list of indented report lines."""
    lines = [
        f"  Command : {ej.job.command}",
        f"  Schedule: {ej.schedule.raw}",
        f"  Meaning : {ej.schedule.description}",
    ]
    if ej.schedule.estimated_runs_per_day is not None:
        runs = ej.schedule.estimated_runs_per_day
        lines.append(f"  Est. runs/day: {runs:.1f}")
    lines.append("")
    return lines


def format_enriched_report(results: List[EnrichedAuditResult]) -> str:
    """Render enriched audit results as a human-readable text report."""
    lines: List[str] = []

    for result in results:
        lines.append(f"=== Host: {result.host} ===")
        if not result.success:
            lines.append(f"  ERROR: {result.error}")
            lines.append("")
            continue

        if not result.enriched_jobs:
            lines.append("  No cron jobs found.")
            lines.append("")
            continue

        for ej in result.enriched_jobs:
            lines.extend(_format_enriched_job(ej))

    return "\n".join(lines)
