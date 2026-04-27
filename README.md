# cron-audit

> A CLI tool to parse, validate, and document cron jobs across remote servers via SSH.

---

## Installation

```bash
pip install cron-audit
```

Or install from source:

```bash
git clone https://github.com/yourname/cron-audit.git && cd cron-audit && pip install .
```

---

## Usage

Audit cron jobs on one or more remote servers:

```bash
cron-audit --host user@192.168.1.10 --host user@192.168.1.11
```

Export results to a JSON or Markdown report:

```bash
cron-audit --host user@myserver.com --output report.md --format markdown
```

Validate cron expressions without connecting to a remote host:

```bash
cron-audit --validate "*/5 * * * * /usr/bin/backup.sh"
```

### Options

| Flag | Description |
|------|-------------|
| `--host` | Remote host in `user@host` format (repeatable) |
| `--output` | Output file path for the report |
| `--format` | Report format: `json`, `markdown`, or `table` (default: `table`) |
| `--validate` | Validate a single cron expression locally |
| `--key` | Path to SSH private key |

---

## Requirements

- Python 3.8+
- SSH access to target servers
- `paramiko`, `croniter`

---

## License

This project is licensed under the [MIT License](LICENSE).