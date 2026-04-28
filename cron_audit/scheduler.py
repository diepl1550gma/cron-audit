"""Utilities for describing cron schedule frequency in human-readable form."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from cron_audit.parser import CronJob

# Special @-strings that map to fixed descriptions
_SPECIAL_DESCRIPTIONS: dict[str, str] = {
    "@reboot": "At system reboot",
    "@yearly": "Once a year (midnight, Jan 1)",
    "@annually": "Once a year (midnight, Jan 1)",
    "@monthly": "Once a month (midnight, 1st)",
    "@weekly": "Once a week (midnight Sunday)",
    "@daily": "Once a day at midnight",
    "@midnight": "Once a day at midnight",
    "@hourly": "Once an hour at minute 0",
}


@dataclass(frozen=True)
class ScheduleSummary:
    """Human-readable description of a cron schedule."""

    raw: str
    description: str
    is_special: bool
    estimated_runs_per_day: Optional[float]


def _field_multiplicity(field: str, max_value: int) -> int:
    """Estimate how many distinct values a single cron field represents."""
    if field == "*":
        return max_value
    if "," in field:
        return len(field.split(","))
    if "/" in field:
        parts = field.split("/")
        step = int(parts[1]) if parts[1].isdigit() else 1
        return max(1, max_value // step)
    return 1


def _estimate_runs_per_day(minute: str, hour: str) -> float:
    """Rough estimate of daily execution count from minute/hour fields."""
    hours = _field_multiplicity(hour, 24)
    minutes = _field_multiplicity(minute, 60)
    return float(hours * minutes)


def describe_schedule(job: CronJob) -> ScheduleSummary:
    """Return a ScheduleSummary for the given CronJob."""
    raw_schedule = job.raw_schedule

    if raw_schedule in _SPECIAL_DESCRIPTIONS:
        return ScheduleSummary(
            raw=raw_schedule,
            description=_SPECIAL_DESCRIPTIONS[raw_schedule],
            is_special=True,
            estimated_runs_per_day=None,
        )

    parts = raw_schedule.split()
    if len(parts) != 5:
        return ScheduleSummary(
            raw=raw_schedule,
            description="Unknown schedule format",
            is_special=False,
            estimated_runs_per_day=None,
        )

    minute, hour, dom, month, dow = parts
    runs = _estimate_runs_per_day(minute, hour)

    desc_parts = []
    if hour == "*" and minute == "*":
        desc_parts.append("every minute")
    elif hour == "*":
        desc_parts.append(f"every hour at minute {minute}")
    elif minute == "0" and hour != "*":
        desc_parts.append(f"at {hour}:00")
    else:
        desc_parts.append(f"at minute {minute} of hour {hour}")

    if dom != "*":
        desc_parts.append(f"on day-of-month {dom}")
    if month != "*":
        desc_parts.append(f"in month {month}")
    if dow != "*":
        desc_parts.append(f"on weekday {dow}")

    description = "Runs " + ", ".join(desc_parts)
    return ScheduleSummary(
        raw=raw_schedule,
        description=description,
        is_special=False,
        estimated_runs_per_day=runs,
    )
