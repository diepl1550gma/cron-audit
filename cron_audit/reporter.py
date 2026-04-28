"""Enriched reporting: combines audit results with schedule descriptions."""

from dataclasses import dataclass, field
from typing import List, Optional
from cron_audit.parser import CronJob
from cron_audit.scheduler import ScheduleSummary, describe_schedule
from cron_audit.remote_audit import AuditResult


@dataclass
class EnrichedJob:
    job: CronJob
    schedule_summary: Optional[ScheduleSummary]


@dataclass
class EnrichedAuditResult:
    host: str
    success: bool
    enriched_jobs: List[EnrichedJob] = field(default_factory=list)
    error: Optional[str] = None


def enrich_audit_result(result: AuditResult) -> EnrichedAuditResult:
    """Attach schedule summaries to each job in an AuditResult."""
    if not result.success or result.jobs is None:
        return EnrichedAuditResult(
            host=result.host,
            success=False,
            error=result.error,
        )

    enriched_jobs = [
        EnrichedJob(job=job, schedule_summary=describe_schedule(job))
        for job in result.jobs
    ]
    return EnrichedAuditResult(
        host=result.host,
        success=True,
        enriched_jobs=enriched_jobs,
    )


def _format_enriched_job(ej: EnrichedJob) -> str:
    summary = ej.schedule_summary
    if summary:
        schedule_str = f"{summary.expression} ({summary.human_readable}, ~{summary.estimated_runs_per_day}/day)"
    else:
        schedule_str = "unknown schedule"
    return f"  {schedule_str}\n    cmd: {ej.job.command}"


def format_enriched_report(enriched: EnrichedAuditResult) -> str:
    """Render an EnrichedAuditResult as a human-readable report string."""
    lines = [f"Host: {enriched.host}"]
    if not enriched.success:
        lines.append(f"  ERROR: {enriched.error}")
        return "\n".join(lines)

    if not enriched.enriched_jobs:
        lines.append("  No cron jobs found.")
        return "\n".join(lines)

    lines.append(f"  {len(enriched.enriched_jobs)} job(s) found:")
    for ej in enriched.enriched_jobs:
        lines.append(_format_enriched_job(ej))
    return "\n".join(lines)
