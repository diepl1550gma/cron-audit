"""Persist and load crontab snapshots to/from JSON for later diffing."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List

from cron_audit.parser import CronJob

# Snapshot file format version — bump when schema changes.
_FORMAT_VERSION = 1


def _job_to_dict(job: CronJob) -> Dict[str, object]:
    return {
        "schedule": job.schedule,
        "command": job.command,
        "raw": job.raw,
        "comment": job.comment,
    }


def _dict_to_job(data: Dict[str, object]) -> CronJob:
    return CronJob(
        schedule=str(data["schedule"]),
        command=str(data["command"]),
        raw=str(data.get("raw", "")),
        comment=str(data.get("comment", "")) or None,  # type: ignore[arg-type]
    )


def save_snapshot(
    path: Path,
    host_jobs: Dict[str, List[CronJob]],
) -> None:
    """Serialise a mapping of host -> jobs to a JSON snapshot file."""
    payload = {
        "version": _FORMAT_VERSION,
        "hosts": {
            host: [_job_to_dict(j) for j in jobs]
            for host, jobs in host_jobs.items()
        },
    }
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def load_snapshot(path: Path) -> Dict[str, List[CronJob]]:
    """Load a snapshot file and return a mapping of host -> jobs.

    Raises:
        ValueError: If the snapshot format version is unsupported.
        FileNotFoundError: If *path* does not exist.
    """
    raw = json.loads(path.read_text(encoding="utf-8"))
    version = raw.get("version", 0)
    if version != _FORMAT_VERSION:
        raise ValueError(
            f"Unsupported snapshot version {version!r}; expected {_FORMAT_VERSION}"
        )
    return {
        host: [_dict_to_job(d) for d in jobs]
        for host, jobs in raw["hosts"].items()
    }
