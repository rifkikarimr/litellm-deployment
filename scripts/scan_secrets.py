#!/usr/bin/env python3
"""Fail on likely credentials, private keys, private IPs, or stale corporate IDs."""

from pathlib import Path
import re
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]
PATTERNS = {
    "Google API key": re.compile("AI" + r"za[0-9A-Za-z_-]{30,}"),
    "OpenAI-style secret": re.compile(r"\b" + "sk" + r"-[0-9A-Za-z_-]{16,}"),
    "private key": re.compile(r"BEGIN [A-Z ]*PRIVATE KEY"),
    "private IPv4": re.compile(
        r"(?<![0-9])(?:10(?:\.[0-9]{1,3}){3}|192\.168(?:\.[0-9]{1,3}){2}|172\.(?:1[6-9]|2[0-9]|3[01])(?:\.[0-9]{1,3}){2})(?![0-9])"
    ),
    "stale corporate identifier": re.compile(
        "corporate" + "-digital", re.IGNORECASE
    ),
    "service-account credential": re.compile(
        r'"(?:private_key|private_key_id|client_email)"\s*:', re.IGNORECASE
    ),
}


def tracked_files() -> list[Path]:
    output = subprocess.check_output(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard", "-z"],
        cwd=ROOT,
    ).decode("utf-8")
    return [ROOT / name for name in output.split("\0") if name]


def main() -> int:
    findings: list[str] = []
    for path in tracked_files():
        if path.resolve() == Path(__file__).resolve():
            continue
        if not path.is_file():
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        for line_number, line in enumerate(text.splitlines(), start=1):
            for label, pattern in PATTERNS.items():
                if pattern.search(line):
                    findings.append(f"{path.relative_to(ROOT)}:{line_number}: {label}")

    if findings:
        print("secret scan: FAIL", file=sys.stderr)
        print("\n".join(findings), file=sys.stderr)
        return 1

    print("secret scan: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
