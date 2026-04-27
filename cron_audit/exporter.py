"""Export audit results to various formats (JSON, CSV, Markdown)."""

from __future__ import annotations

import csv
import io
import json
from typing import List

from cron_audit.remote_audit import AuditResult


def export_json(results: List[AuditResult], indent: int = 2) -> str:
    """Serialize audit results to a JSON string."""
    payload = []
    for result in results:
        entry: dict = {
            "host": result.host,
            "success": result.success,
            "error": result.error,
            "jobs": [],
        }
        if result.jobs:
            for job in result.jobs:
                entry["jobs"].append({
                    "raw": job.raw,
                    "minute": job.minute,
                    "hour": job.hour,
                    "day_of_month": job.day_of_month,
                    "month": job.month,
                    "day_of_week": job.day_of_week,
                    "command": job.command,
                    "special": job.special,
                })
        payload.append(entry)
    return json.dumps(payload, indent=indent)


def export_csv(results: List[AuditResult]) -> str:
    """Serialize audit results to a CSV string."""
    output = io.StringIO()
    fieldnames = [
        "host", "success", "error",
        "minute", "hour", "day_of_month", "month", "day_of_week",
        "command", "special", "raw",
    ]
    writer = csv.DictWriter(output, fieldnames=fieldnames)
    writer.writeheader()
    for result in results:
        if not result.jobs:
            writer.writerow({
                "host": result.host,
                "success": result.success,
                "error": result.error or "",
                "minute": "", "hour": "", "day_of_month": "",
                "month": "", "day_of_week": "", "command": "",
                "special": "", "raw": "",
            })
        else:
            for job in result.jobs:
                writer.writerow({
                    "host": result.host,
                    "success": result.success,
                    "error": "",
                    "minute": job.minute or "",
                    "hour": job.hour or "",
                    "day_of_month": job.day_of_month or "",
                    "month": job.month or "",
                    "day_of_week": job.day_of_week or "",
                    "command": job.command,
                    "special": job.special or "",
                    "raw": job.raw,
                })
    return output.getvalue()


def export_markdown(results: List[AuditResult]) -> str:
    """Serialize audit results to a Markdown table string."""
    lines = []
    for result in results:
        lines.append(f"## Host: {result.host}")
        if not result.success:
            lines.append(f"\n**Error:** {result.error}\n")
            continue
        if not result.jobs:
            lines.append("\n_No cron jobs found._\n")
            continue
        lines.append("")
        lines.append("| Minute | Hour | DOM | Month | DOW | Command | Special |")
        lines.append("|--------|------|-----|-------|-----|---------|---------|")
        for job in result.jobs:
            lines.append(
                f"| {job.minute or ''} | {job.hour or ''} | {job.day_of_month or ''} "
                f"| {job.month or ''} | {job.day_of_week or ''} "
                f"| {job.command} | {job.special or ''} |"
            )
        lines.append("")
    return "\n".join(lines)
