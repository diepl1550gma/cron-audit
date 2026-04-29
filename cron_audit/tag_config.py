"""Load tag rules from YAML or dict configuration."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List

try:
    import yaml
    _YAML_AVAILABLE = True
except ImportError:  # pragma: no cover
    _YAML_AVAILABLE = False

from cron_audit.tagger import TagRule


def _parse_rule(raw: Dict[str, Any]) -> TagRule:
    """Parse a single rule dict into a TagRule."""
    pattern = raw.get("pattern", "")
    tags = raw.get("tags", [])
    if not pattern:
        raise ValueError("Tag rule missing 'pattern' field")
    if not tags:
        raise ValueError(f"Tag rule for pattern '{pattern}' has no tags")
    return TagRule(pattern=pattern, tags=list(tags))


def load_tag_rules_from_dict(data: Dict[str, Any]) -> List[TagRule]:
    """Load tag rules from a parsed config dictionary."""
    raw_rules = data.get("rules", [])
    return [_parse_rule(r) for r in raw_rules]


def load_tag_rules(path: str) -> List[TagRule]:
    """Load tag rules from a YAML file."""
    if not _YAML_AVAILABLE:  # pragma: no cover
        raise RuntimeError("PyYAML is required to load tag config files")
    config_path = Path(path)
    if not config_path.exists():
        raise FileNotFoundError(f"Tag config file not found: {path}")
    with config_path.open("r") as fh:
        data = yaml.safe_load(fh) or {}
    return load_tag_rules_from_dict(data)
