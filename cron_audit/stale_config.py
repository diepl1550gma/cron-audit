"""Load stale-detection configuration from YAML or dict."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import List

try:
    import yaml
    _YAML_AVAILABLE = True
except ImportError:  # pragma: no cover
    _YAML_AVAILABLE = False


@dataclass
class StalenessConfig:
    """Configuration controlling stale-job detection behaviour."""
    extra_noop_commands: List[str] = field(default_factory=list)
    extra_stale_comment_patterns: List[str] = field(default_factory=list)
    ignore_hosts: List[str] = field(default_factory=list)


def load_staleness_config_from_dict(raw: dict) -> StalenessConfig:
    return StalenessConfig(
        extra_noop_commands=raw.get("extra_noop_commands", []),
        extra_stale_comment_patterns=raw.get("extra_stale_comment_patterns", []),
        ignore_hosts=raw.get("ignore_hosts", []),
    )


def load_staleness_config(path: str | Path) -> StalenessConfig:
    """Load staleness config from a YAML file; return defaults if missing."""
    p = Path(path)
    if not p.exists():
        return StalenessConfig()
    if not _YAML_AVAILABLE:  # pragma: no cover
        raise RuntimeError("PyYAML is required to load stale config files.")
    with p.open() as fh:
        raw = yaml.safe_load(fh) or {}
    return load_staleness_config_from_dict(raw.get("staleness", raw))
