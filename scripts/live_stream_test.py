#!/usr/bin/env python3
"""Run one explicitly approved streaming request through the local gateway."""

import json
import os
from pathlib import Path
import sys
import time
import urllib.error
import urllib.request

from dotenv import load_dotenv


load_dotenv(Path(__file__).resolve().parents[1] / ".env")

BASE_URL = os.getenv("LITELLM_BASE_URL", "http://127.0.0.1:4000").rstrip("/")
API_KEY = os.getenv("LITELLM_API_KEY") or os.getenv("LITELLM_MASTER_KEY")
MODEL = os.getenv("LITELLM_MODEL", "general-chat")
EXPECTED_TEXT = os.getenv("LITELLM_EXPECTED_TEXT", "STREAM_OK")


def main() -> int:
    if os.getenv("RUN_PAID_PROVIDER_TESTS") != "1":
        print("Set RUN_PAID_PROVIDER_TESTS=1 to confirm this paid provider test.")
        return 2
    if not API_KEY or API_KEY == "replace-me":
        print("Set a non-placeholder LITELLM_API_KEY or LITELLM_MASTER_KEY.")
        return 2

    payload = {
        "model": MODEL,
        "messages": [
            {"role": "user", "content": f"Reply with exactly: {EXPECTED_TEXT}"}
        ],
        "max_tokens": 32,
        "reasoning_effort": "low",
        "stream": True,
    }
    request = urllib.request.Request(
        f"{BASE_URL}/v1/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {API_KEY}",
            "Content-Type": "application/json",
        },
        method="POST",
    )

    started = time.monotonic()
    chunks = 0
    content_parts: list[str] = []
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            model_id = response.headers.get("x-litellm-model-id", "not-returned")
            for raw_line in response:
                line = raw_line.decode("utf-8").strip()
                if not line.startswith("data: ") or line == "data: [DONE]":
                    continue
                event = json.loads(line.removeprefix("data: "))
                chunks += 1
                delta = event.get("choices", [{}])[0].get("delta", {})
                if delta.get("content"):
                    content_parts.append(delta["content"])
            elapsed_ms = round((time.monotonic() - started) * 1000)
            content = "".join(content_parts).strip()
            print(f"status={response.status}")
            print(f"requested_alias={MODEL}")
            print(f"model_id={model_id}")
            print(f"chunks={chunks}")
            print(f"latency_ms={elapsed_ms}")
            print(f"content={content if content else '<empty>'}")
            return 0 if content == EXPECTED_TEXT and chunks > 0 else 1
    except urllib.error.HTTPError as exc:
        print(f"streaming test failed: HTTP {exc.code}", file=sys.stderr)
        return 1
    except (OSError, KeyError, ValueError) as exc:
        print(f"streaming test failed: {type(exc).__name__}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
