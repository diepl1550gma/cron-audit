"""Load and validate filter configuration from a YAML or dict source."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from cron_audit.filter import FilterCriteria


@dataclass
class FilterConfig:
    """Parsed and validated filter configuration."""

    criteria: FilterCriteria
    label: str = "unnamed"


_VALID_KEYS = {
    "label",
    "user",
    "command_pattern",
    "special_string",
    "min_runs_per_day",
    "max_runs_per_day",
}


def load_filter_config(raw: Dict[str, Any]) -> FilterConfig:
    """Parse a dict (e.g. from YAML) into a FilterConfig.

    Raises ValueError for unknown keys or invalid types.
    """
    unknown = set(raw.keys()) - _VALID_KEYS
    if unknown:
        raise ValueError(f"Unknown filter config keys: {sorted(unknown)}")

    label = str(raw.get("label", "unnamed"))

    min_rpd = raw.get("min_runs_per_day")
    max_rpd = raw.get("max_runs_per_day")

    if min_rpd is not None:
        try:
            min_rpd = float(min_rpd)
        except (TypeError, ValueError):
            raise ValueError(f"min_runs_per_day must be numeric, got {min_rpd!r}")

    if max_rpd is not None:
        try:
            max_rpd = float(max_rpd)
        except (TypeError, ValueError):
            raise ValueError(f"max_runs_per_day must be numeric, got {max_rpd!r}")

    criteria = FilterCriteria(
        user=raw.get("user"),
        command_pattern=raw.get("command_pattern"),
        special_string=raw.get("special_string"),
        min_runs_per_day=min_rpd,
        max_runs_per_day=max_rpd,
    )

    return FilterConfig(criteria=criteria, label=label)


def load_filter_configs(raw_list: List[Dict[str, Any]]) -> List[FilterConfig]:
    """Parse a list of raw dicts into FilterConfig objects."""
    return [load_filter_config(item) for item in raw_list]
