"""CLI integration for risk scoring of audited cron jobs."""

from __future__ import annotations

from typing import Dict, List

from cron_audit.remote_audit import AuditResult
from cron_audit.risk_scorer import RiskScore, score_jobs


def run_risk_scoring(
    results: List[AuditResult],
    min_level: str = "low",
) -> Dict[str, List[RiskScore]]:
    """Return a mapping of host -> risk scores, filtered by minimum level."""
    _level_order = {"low": 0, "medium": 1, "high": 2, "critical": 3}
    min_rank = _level_order.get(min_level, 0)

    output: Dict[str, List[RiskScore]] = {}
    for result in results:
        if not result.success or result.jobs is None:
            output[result.host] = []
            continue
        scored = score_jobs(result.jobs)
        filtered = [r for r in scored if _level_order.get(r.level, 0) >= min_rank]
        output[result.host] = filtered
    return output


def has_any_high_risk(scored: Dict[str, List[RiskScore]]) -> bool:
    """Return True if any host has at least one high or critical risk job."""
    for scores in scored.values():
        for r in scores:
            if r.level in ("high", "critical"):
                return True
    return False


def print_risk_report(scored: Dict[str, List[RiskScore]]) -> None:
    """Print a human-readable risk report to stdout."""
    for host, scores in scored.items():
        print(f"\n[{host}]")
        if not scores:
            print("  No risk issues found.")
            continue
        for rs in scores:
            label = f"[{rs.level.upper()}] score={rs.score}"
            print(f"  {label}  {rs.job.command[:60]}")
            for reason in rs.reasons:
                print(f"    - {reason}")
