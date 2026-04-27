"""Orchestrate fetching and parsing crontabs from one or more remote hosts."""

import logging
from dataclasses import dataclass, field
from typing import Optional

from cron_audit.crontab_reader import parse_crontab, summarize_jobs
from cron_audit.ssh_client import RemoteCrontab, SSHConfig, fetch_crontab

logger = logging.getLogger(__name__)


@dataclass
class AuditResult:
    hostname: str
    username: str
    summary: dict = field(default_factory=dict)
    error: Optional[str] = None

    @property
    def success(self) -> bool:
        return self.error is None


def audit_host(config: SSHConfig) -> AuditResult:
    """Fetch and parse the crontab for a single remote host."""
    remote: RemoteCrontab = fetch_crontab(config)

    if not remote.success:
        return AuditResult(
            hostname=config.hostname,
            username=config.username,
            error=remote.error,
        )

    jobs = parse_crontab(remote.raw_lines)
    summary = summarize_jobs(jobs)
    logger.info(
        "Audit complete for %s: %d valid job(s), %d skipped",
        config.hostname,
        summary.get("total_jobs", 0),
        summary.get("skipped_lines", 0),
    )
    return AuditResult(
        hostname=config.hostname,
        username=config.username,
        summary=summary,
    )


def audit_hosts(configs: list[SSHConfig]) -> list[AuditResult]:
    """Run audits sequentially across multiple hosts and return all results."""
    results = []
    for config in configs:
        logger.debug("Starting audit for host: %s", config.hostname)
        results.append(audit_host(config))
    return results


def format_audit_report(results: list[AuditResult]) -> str:
    """Produce a human-readable report from a list of AuditResult objects."""
    lines = []
    for result in results:
        lines.append(f"=== {result.username}@{result.hostname} ===")
        if not result.success:
            lines.append(f"  ERROR: {result.error}")
        else:
            s = result.summary
            lines.append(f"  Total jobs  : {s.get('total_jobs', 0)}")
            lines.append(f"  Skipped     : {s.get('skipped_lines', 0)}")
            for job in s.get("jobs", []):
                lines.append(f"  - {job.get('command', '')}  [{job.get('schedule', '')}]")
        lines.append("")
    return "\n".join(lines)
