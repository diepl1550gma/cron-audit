"""CLI helpers for saving and comparing cron snapshots."""

from __future__ import annotations

import os
from typing import List, Optional

from cron_audit.differ import CronDiff, diff_crontabs, format_diff_report, has_changes
from cron_audit.remote_audit import AuditResult
from cron_audit.snapshot import load_snapshot, save_snapshot


def snapshot_hosts(
    results: List[AuditResult],
    snapshot_dir: str,
) -> List[str]:
    """Persist successful audit results as snapshots.

    Returns a list of file paths that were written.
    """
    written: List[str] = []
    os.makedirs(snapshot_dir, exist_ok=True)
    for result in results:
        if result.success and result.jobs is not None:
            path = os.path.join(snapshot_dir, f"{result.host}.json")
            save_snapshot(result.host, result.jobs, path)
            written.append(path)
    return written


def diff_against_snapshots(
    results: List[AuditResult],
    snapshot_dir: str,
) -> List[CronDiff]:
    """Compare current audit results against previously saved snapshots.

    Hosts with no existing snapshot are skipped.
    """
    diffs: List[CronDiff] = []
    for result in results:
        if not result.success or result.jobs is None:
            continue
        path = os.path.join(snapshot_dir, f"{result.host}.json")
        if not os.path.exists(path):
            continue
        previous = load_snapshot(path)
        diff = diff_crontabs(result.host, previous, result.jobs)
        diffs.append(diff)
    return diffs


def print_diff_reports(
    diffs: List[CronDiff],
    only_changes: bool = False,
) -> None:
    """Print formatted diff reports to stdout."""
    for diff in diffs:
        if only_changes and not has_changes(diff):
            continue
        print(format_diff_report(diff))
        print()


def has_any_changes(diffs: List[CronDiff]) -> bool:
    """Return True if any diff contains at least one change."""
    return any(has_changes(d) for d in diffs)
