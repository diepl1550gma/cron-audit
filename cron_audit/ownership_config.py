"""Load ownership rules from YAML/dict configuration."""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List

from cron_audit.ownership import OwnershipRule

try:
    import yaml
except ImportError:  # pragma: no cover
    yaml = None  # type: ignore


def _parse_rule(raw: Dict[str, Any]) -> OwnershipRule:
    """Parse a single rule dict into an OwnershipRule."""
    pattern = raw.get("pattern", "")
    owner = raw.get("owner", "unknown")
    team = raw.get("team", "unknown")
    if not pattern:
        raise ValueError(f"Ownership rule missing 'pattern': {raw}")
    return OwnershipRule(pattern=pattern, owner=owner, team=team)


def load_ownership_rules_from_dict(data: Dict[str, Any]) -> List[OwnershipRule]:
    """Load ownership rules from a parsed config dictionary."""
    raw_rules = data.get("ownership_rules", [])
    return [_parse_rule(r) for r in raw_rules]


def load_ownership_rules(path: str | Path) -> List[OwnershipRule]:
    """Load ownership rules from a YAML file."""
    if yaml is None:  # pragma: no cover
        raise RuntimeError("PyYAML is required to load ownership config files.")
    with open(path, "r") as fh:
        data = yaml.safe_load(fh) or {}
    return load_ownership_rules_from_dict(data)
