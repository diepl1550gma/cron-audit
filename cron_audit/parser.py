"""Cron expression parser and validator."""

import re
from dataclasses import dataclass
from typing import Optional

CRON_FIELD_RANGES = {
    "minute": (0, 59),
    "hour": (0, 23),
    "day_of_month": (1, 31),
    "month": (1, 12),
    "day_of_week": (0, 7),
}

SPECIAL_STRINGS = {"@reboot", "@yearly", "@annually", "@monthly", "@weekly", "@daily", "@midnight", "@hourly"}


@dataclass
class CronJob:
    raw_line: str
    schedule: str
    command: str
    user: Optional[str] = None
    is_valid: bool = True
    error: Optional[str] = None


def _validate_field(value: str, min_val: int, max_val: int) -> bool:
    """Validate a single cron field."""
    if value == "*":
        return True
    step_match = re.match(r"^\*/?(\d+)$", value)
    if step_match:
        return int(step_match.group(1)) >= 1
    range_match = re.match(r"^(\d+)-(\d+)$", value)
    if range_match:
        lo, hi = int(range_match.group(1)), int(range_match.group(2))
        return min_val <= lo <= hi <= max_val
    if re.match(r"^\d+$", value):
        return min_val <= int(value) <= max_val
    if "," in value:
        return all(_validate_field(part, min_val, max_val) for part in value.split(","))
    return False


def parse_cron_line(line: str) -> Optional[CronJob]:
    """Parse a single cron line and return a CronJob or None if comment/empty."""
    stripped = line.strip()
    if not stripped or stripped.startswith("#"):
        return None

    if any(stripped.startswith(s) for s in SPECIAL_STRINGS):
        parts = stripped.split(None, 1)
        schedule = parts[0]
        command = parts[1] if len(parts) > 1 else ""
        return CronJob(raw_line=line, schedule=schedule, command=command)

    parts = stripped.split()
    if len(parts) < 6:
        return CronJob(raw_line=line, schedule="", command=stripped, is_valid=False,
                       error="Insufficient fields in cron expression")

    fields = parts[:5]
    command = " ".join(parts[5:])
    schedule = " ".join(fields)

    field_names = list(CRON_FIELD_RANGES.keys())
    for i, (field, name) in enumerate(zip(fields, field_names)):
        lo, hi = CRON_FIELD_RANGES[name]
        if not _validate_field(field, lo, hi):
            return CronJob(raw_line=line, schedule=schedule, command=command,
                           is_valid=False, error=f"Invalid value '{field}' for field '{name}'")

    return CronJob(raw_line=line, schedule=schedule, command=command)
