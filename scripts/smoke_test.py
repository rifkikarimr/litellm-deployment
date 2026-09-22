#!/usr/bin/env python3
"""Check the running gateway without invoking a paid model."""

import os
import http.client
import sys
import urllib.error
import urllib.request


BASE_URL = os.getenv("LITELLM_BASE_URL", "http://127.0.0.1:4000").rstrip("/")


def main() -> int:
    try:
        with urllib.request.urlopen(f"{BASE_URL}/health/liveliness", timeout=10) as response:
            print(f"health: PASS ({response.status})")
            return 0 if response.status == 200 else 1
    except (urllib.error.URLError, http.client.HTTPException, OSError, TimeoutError) as exc:
        print(f"health: FAIL ({exc})", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
