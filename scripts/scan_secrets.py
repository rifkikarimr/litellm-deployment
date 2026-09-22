#!/usr/bin/env python3
"""Fail on likely credentials, private keys, private IPs, or stale corporate IDs."""

import argparse
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


def scan_text(text: str, display_path: str) -> set[str]:
    findings: set[str] = set()
    for line_number, line in enumerate(text.splitlines(), start=1):
        for label, pattern in PATTERNS.items():
            if pattern.search(line):
                findings.add(f"{display_path}:{line_number}: {label}")
    return findings


def scan_current_tree() -> set[str]:
    findings: set[str] = set()
    for path in tracked_files():
        if path.resolve() == Path(__file__).resolve():
            continue
        if not path.is_file():
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        findings.update(scan_text(text, str(path.relative_to(ROOT))))
    return findings


def scan_history() -> set[str]:
    """Scan each unique blob reachable from local refs without printing values."""
    findings: set[str] = set()
    seen_blobs: set[str] = set()
    commits = subprocess.check_output(
        ["git", "rev-list", "--all"], cwd=ROOT, text=True
    ).splitlines()

    for commit in commits:
        entries = subprocess.check_output(
            ["git", "ls-tree", "-r", "-z", commit], cwd=ROOT
        ).split(b"\0")
        for entry in entries:
            if not entry:
                continue
            metadata, raw_path = entry.split(b"\t", maxsplit=1)
            blob = metadata.split()[2].decode("ascii")
            if blob in seen_blobs:
                continue
            seen_blobs.add(blob)
            path = raw_path.decode("utf-8", errors="replace")
            data = subprocess.check_output(
                ["git", "cat-file", "blob", blob], cwd=ROOT
            )
            try:
                text = data.decode("utf-8")
            except UnicodeDecodeError:
                continue
            findings.update(scan_text(text, f"history:{path}"))
    return findings


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--history",
        action="store_true",
        help="scan every unique blob reachable from local Git refs",
    )
    args = parser.parse_args()

    findings = scan_history() if args.history else scan_current_tree()

    if findings:
        scope = "history" if args.history else "current tree"
        print(f"secret scan ({scope}): FAIL", file=sys.stderr)
        print("\n".join(sorted(findings)), file=sys.stderr)
        return 1

    scope = "history" if args.history else "current tree"
    print(f"secret scan ({scope}): PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
