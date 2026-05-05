"""Load baseline configurations from YAML or JSON files."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

try:
    import yaml  # type: ignore
    _YAML_AVAILABLE = True
except ImportError:  # pragma: no cover
    _YAML_AVAILABLE = False


def _load_raw(path: Path) -> Any:
    text = path.read_text(encoding="utf-8")
    suffix = path.suffix.lower()
    if suffix in (".yaml", ".yml"):
        if not _YAML_AVAILABLE:  # pragma: no cover
            raise RuntimeError("PyYAML is required to load YAML baseline files.")
        return yaml.safe_load(text)
    return json.loads(text)


def load_baseline_for_host(path: Path, host: str) -> List[Dict]:
    """Return the list of approved jobs for *host* from *path*.

    File format (JSON / YAML)::

        {
          "web-01": [
            {"command": "/usr/bin/backup.sh", "schedule": "0 2 * * *"}
          ]
        }

    Returns an empty list when the host is not present in the file.
    """
    raw = _load_raw(path)
    if not isinstance(raw, dict):
        raise ValueError(f"Baseline file {path} must be a mapping of host -> jobs.")
    return raw.get(host, [])


def load_all_baselines(path: Path) -> Dict[str, List[Dict]]:
    """Return the full host -> jobs mapping from *path*."""
    raw = _load_raw(path)
    if not isinstance(raw, dict):
        raise ValueError(f"Baseline file {path} must be a mapping of host -> jobs.")
    return {host: jobs for host, jobs in raw.items()}
