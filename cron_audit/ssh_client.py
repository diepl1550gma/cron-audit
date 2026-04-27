"""SSH client utilities for connecting to remote servers and fetching crontabs."""

import logging
from dataclasses import dataclass, field
from typing import Optional

try:
    import paramiko
except ImportError:
    paramiko = None  # type: ignore

logger = logging.getLogger(__name__)

DEFAULT_PORT = 22
DEFAULT_TIMEOUT = 10


@dataclass
class SSHConfig:
    hostname: str
    username: str
    port: int = DEFAULT_PORT
    password: Optional[str] = None
    key_filename: Optional[str] = None
    timeout: float = DEFAULT_TIMEOUT


@dataclass
class RemoteCrontab:
    hostname: str
    username: str
    raw_lines: list[str] = field(default_factory=list)
    error: Optional[str] = None

    @property
    def success(self) -> bool:
        return self.error is None


def fetch_crontab(config: SSHConfig) -> RemoteCrontab:
    """Connect to a remote host via SSH and retrieve the user's crontab."""
    if paramiko is None:
        raise RuntimeError("paramiko is required for SSH support: pip install paramiko")

    result = RemoteCrontab(hostname=config.hostname, username=config.username)

    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    try:
        logger.debug("Connecting to %s@%s:%d", config.username, config.hostname, config.port)
        client.connect(
            hostname=config.hostname,
            port=config.port,
            username=config.username,
            password=config.password,
            key_filename=config.key_filename,
            timeout=config.timeout,
        )
        _, stdout, stderr = client.exec_command("crontab -l 2>/dev/null")
        output = stdout.read().decode("utf-8", errors="replace")
        err_output = stderr.read().decode("utf-8", errors="replace").strip()

        if err_output:
            logger.warning("stderr from %s: %s", config.hostname, err_output)

        result.raw_lines = output.splitlines()
        logger.info("Fetched %d crontab lines from %s", len(result.raw_lines), config.hostname)
    except Exception as exc:  # noqa: BLE001
        logger.error("Failed to fetch crontab from %s: %s", config.hostname, exc)
        result.error = str(exc)
    finally:
        client.close()

    return result
