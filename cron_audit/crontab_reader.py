"""Read and parse crontab content from a string or list of lines."""

from typing import List
from cron_audit.parser import CronJob, parse_cron_line


def parse_crontab(content: str, user: str = None) -> List[CronJob]:
    """
    Parse a full crontab file content into a list of CronJob objects.

    Args:
        content: Raw crontab file content as a string.
        user: Optional username to associate with each job.

    Returns:
        List of CronJob instances (comments and blanks excluded).
    """
    jobs = []
    for line in content.splitlines():
        job = parse_cron_line(line)
        if job is not None:
            if user:
                job.user = user
            jobs.append(job)
    return jobs


def summarize_jobs(jobs: List[CronJob]) -> dict:
    """
    Produce a summary dictionary for a list of parsed cron jobs.

    Returns:
        A dict with total, valid, and invalid counts plus a list of errors.
    """
    total = len(jobs)
    valid = [j for j in jobs if j.is_valid]
    invalid = [j for j in jobs if not j.is_valid]
    return {
        "total": total,
        "valid": len(valid),
        "invalid": len(invalid),
        "errors": [
            {"line": j.raw_line.strip(), "error": j.error}
            for j in invalid
        ],
    }
