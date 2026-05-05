"""CLI helpers for baseline checking."""
from __future__ import annotations

from pathlib import Path
from typing import List

from cron_audit.baseline import BaselineReport, check_against_baseline, format_baseline_report
from cron_audit.baseline_config import load_all_baselines
from cron_audit.remote_audit import AuditResult


def run_baseline_check(
    results: List[AuditResult],
    baseline_path: Path,
) -> List[BaselineReport]:
    """Run baseline checks for every host in *results*.

    Hosts absent from the baseline file are treated as having an empty
    approved list (every job is a violation).
    """
    all_baselines = load_all_baselines(baseline_path)
    reports: List[BaselineReport] = []
    for result in results:
        approved = all_baselines.get(result.host, [])
        reports.append(check_against_baseline(result, approved))
    return reports


def print_baseline_reports(reports: List[BaselineReport]) -> None:
    for report in reports:
        print(format_baseline_report(report))


def has_any_violations(reports: List[BaselineReport]) -> bool:
    return any(r.has_violations for r in reports)
