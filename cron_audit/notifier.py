"""Notification module for cron-audit: alert on suspicious or high-frequency cron jobs."""

from dataclasses import dataclass, field
from typing import List, Optional
from cron_audit.reporter import EnrichedJob, EnrichedAuditResult


# Threshold: jobs running more than this many times per day are flagged
HIGH_FREQUENCY_THRESHOLD = 48  # every 30 minutes or more frequent


@dataclass
class Notification:
    level: str  # "warning" or "info"
    host: str
    message: str
    job_command: Optional[str] = None


@dataclass
class NotificationReport:
    host: str
    notifications: List[Notification] = field(default_factory=list)

    @property
    def has_warnings(self) -> bool:
        return any(n.level == "warning" for n in self.notifications)


def _check_job(host: str, enriched_job: EnrichedJob) -> List[Notification]:
    """Inspect a single enriched job and return any notifications."""
    notes: List[Notification] = []
    summary = enriched_job.schedule_summary
    job = enriched_job.job

    if summary is None:
        return notes

    if summary.estimated_runs_per_day >= HIGH_FREQUENCY_THRESHOLD:
        notes.append(
            Notification(
                level="warning",
                host=host,
                message=(
                    f"High-frequency job: ~{summary.estimated_runs_per_day} runs/day "
                    f"({summary.human_readable})"
                ),
                job_command=job.command,
            )
        )

    if job.command.strip().startswith("rm ") or "rm -rf" in job.command:
        notes.append(
            Notification(
                level="warning",
                host=host,
                message="Potentially destructive command detected: starts with 'rm'",
                job_command=job.command,
            )
        )

    return notes


def build_notification_report(enriched: EnrichedAuditResult) -> NotificationReport:
    """Build a NotificationReport from an EnrichedAuditResult."""
    report = NotificationReport(host=enriched.host)

    if not enriched.success:
        report.notifications.append(
            Notification(
                level="warning",
                host=enriched.host,
                message=f"Audit failed: {enriched.error}",
            )
        )
        return report

    for enriched_job in enriched.enriched_jobs:
        report.notifications.extend(_check_job(enriched.host, enriched_job))

    if not report.notifications:
        report.notifications.append(
            Notification(
                level="info",
                host=enriched.host,
                message="No issues detected.",
            )
        )

    return report


def format_notification_report(report: NotificationReport) -> str:
    """Render a NotificationReport as a human-readable string."""
    lines = [f"Notifications for {report.host}:", "-" * 40]
    for note in report.notifications:
        tag = f"[{note.level.upper()}]"
        cmd = f" | cmd: {note.job_command}" if note.job_command else ""
        lines.append(f"  {tag} {note.message}{cmd}")
    return "\n".join(lines)
