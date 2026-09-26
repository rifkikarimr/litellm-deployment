#!/usr/bin/env python3
"""Safely align an initialized Compose PostgreSQL role with the local .env."""

from __future__ import annotations

from datetime import datetime, timezone
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from urllib.parse import unquote, urlparse


ROOT = Path(__file__).resolve().parents[1]
REQUIRED = ("POSTGRES_USER", "POSTGRES_DB", "POSTGRES_PASSWORD", "DATABASE_URL")


def load_env(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def validate_settings(values: dict[str, str]) -> None:
    missing = [key for key in REQUIRED if not values.get(key)]
    if missing:
        raise ValueError(f"missing required .env values: {', '.join(missing)}")

    password = values["POSTGRES_PASSWORD"]
    if password == "replace-me":
        raise ValueError("POSTGRES_PASSWORD is still the example placeholder")
    if "\n" in password or "\r" in password:
        raise ValueError("POSTGRES_PASSWORD must not contain newline characters")

    parsed = urlparse(values["DATABASE_URL"])
    if parsed.scheme not in {"postgres", "postgresql"}:
        raise ValueError("DATABASE_URL must use the postgres or postgresql scheme")
    if parsed.hostname != "postgres":
        raise ValueError("DATABASE_URL host must be the Compose service name 'postgres'")
    if parsed.username != values["POSTGRES_USER"]:
        raise ValueError("DATABASE_URL user does not match POSTGRES_USER")
    if parsed.path.lstrip("/") != values["POSTGRES_DB"]:
        raise ValueError("DATABASE_URL database does not match POSTGRES_DB")
    if unquote(parsed.password or "") != password:
        raise ValueError("DATABASE_URL password does not match POSTGRES_PASSWORD")


def run(command: list[str], **kwargs: object) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(command, cwd=ROOT, check=True, **kwargs)


def main() -> int:
    env_path = ROOT / ".env"
    if not env_path.is_file():
        print("Copy .env.example to .env and configure it first.", file=sys.stderr)
        return 2

    try:
        values = load_env(env_path)
        validate_settings(values)
    except ValueError as exc:
        print(f"database password sync aborted: {exc}", file=sys.stderr)
        return 2

    postgres_id = subprocess.run(
        ["docker", "compose", "ps", "--status", "running", "-q", "postgres"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    if not postgres_id:
        print("database password sync aborted: PostgreSQL is not running", file=sys.stderr)
        return 2

    run(["docker", "compose", "stop", "litellm"])

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    backup_path = Path(tempfile.gettempdir()) / f"litellm-pre-password-sync-{timestamp}.dump"
    backup_fd = os.open(backup_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        with os.fdopen(backup_fd, "wb") as backup_file:
            run(
                [
                    "docker",
                    "compose",
                    "exec",
                    "-T",
                    "postgres",
                    "pg_dump",
                    "-U",
                    values["POSTGRES_USER"],
                    "-d",
                    values["POSTGRES_DB"],
                    "-Fc",
                ],
                stdout=backup_file,
            )
    except Exception:
        backup_path.unlink(missing_ok=True)
        raise

    if backup_path.stat().st_size == 0:
        backup_path.unlink(missing_ok=True)
        print("database password sync aborted: backup is empty", file=sys.stderr)
        return 1

    shell_script = r"""
set -eu
IFS= read -r NEW_DB_PASSWORD
export NEW_DB_PASSWORD
printf '%s\n' \
  '\getenv role_name POSTGRES_USER' \
  '\getenv new_password NEW_DB_PASSWORD' \
  'ALTER ROLE :"role_name" PASSWORD :'"'"'new_password'"'"';' |
  psql -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB"
"""
    run(
        ["docker", "compose", "exec", "-T", "postgres", "sh", "-c", shell_script],
        input=(values["POSTGRES_PASSWORD"] + "\n").encode("utf-8"),
    )
    run(["docker", "compose", "up", "-d", "litellm"])

    print(f"database backup created: {backup_path}")
    print("database role password synchronized; LiteLLM restart requested")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
