"""Command-line interface for cron-audit."""

from __future__ import annotations

import argparse
import sys
from typing import List

from cron_audit.ssh_client import SSHConfig
from cron_audit.remote_audit import audit_hosts
from cron_audit.exporter import export_json, export_csv, export_markdown


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="cron-audit",
        description="Parse, validate, and document cron jobs across remote servers.",
    )
    parser.add_argument(
        "hosts",
        nargs="+",
        metavar="HOST",
        help="Remote host(s) to audit (e.g. user@hostname).",
    )
    parser.add_argument(
        "-p", "--port",
        type=int,
        default=22,
        help="SSH port (default: 22).",
    )
    parser.add_argument(
        "-i", "--identity",
        dest="key_path",
        default=None,
        metavar="KEY",
        help="Path to SSH private key file.",
    )
    parser.add_argument(
        "-f", "--format",
        choices=["json", "csv", "markdown", "text"],
        default="text",
        help="Output format (default: text).",
    )
    parser.add_argument(
        "-o", "--output",
        default=None,
        metavar="FILE",
        help="Write output to FILE instead of stdout.",
    )
    return parser


def _build_configs(args: argparse.Namespace) -> List[SSHConfig]:
    configs = []
    for host_spec in args.hosts:
        if "@" in host_spec:
            username, hostname = host_spec.split("@", 1)
        else:
            username, hostname = "root", host_spec
        configs.append(SSHConfig(
            hostname=hostname,
            username=username,
            port=args.port,
            key_path=args.key_path,
        ))
    return configs


def run(argv: List[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    configs = _build_configs(args)
    results = audit_hosts(configs)

    fmt = args.format
    if fmt == "json":
        output = export_json(results)
    elif fmt == "csv":
        output = export_csv(results)
    elif fmt == "markdown":
        output = export_markdown(results)
    else:
        from cron_audit.remote_audit import format_audit_report
        output = format_audit_report(results)

    if args.output:
        with open(args.output, "w", encoding="utf-8") as fh:
            fh.write(output)
        print(f"Report written to {args.output}")
    else:
        print(output)

    failed = sum(1 for r in results if not r.success)
    return 1 if failed else 0


def main() -> None:
    sys.exit(run())


if __name__ == "__main__":
    main()
