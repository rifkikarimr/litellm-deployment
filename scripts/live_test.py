#!/usr/bin/env python3
"""Run an explicitly requested paid-provider integration test through LiteLLM."""

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
EXPECTED_TEXT = os.getenv("LITELLM_EXPECTED_TEXT", "ready")
MAX_TOKENS = int(os.getenv("LITELLM_MAX_TOKENS", "16"))
REASONING_EFFORT = os.getenv("LITELLM_REASONING_EFFORT", "low")


def main() -> int:
    if os.getenv("RUN_PAID_PROVIDER_TESTS") != "1":
        print("Set RUN_PAID_PROVIDER_TESTS=1 to confirm this paid provider test.", file=sys.stderr)
        return 2
    if not API_KEY:
        print("Set LITELLM_API_KEY or LITELLM_MASTER_KEY.", file=sys.stderr)
        return 2
    if API_KEY == "replace-me":
        print("Replace the placeholder LiteLLM key before running this test.", file=sys.stderr)
        return 2

    payload = {
        "model": MODEL,
        "messages": [
            {"role": "user", "content": f"Reply with exactly: {EXPECTED_TEXT}"}
        ],
        "max_tokens": MAX_TOKENS,
        "reasoning_effort": REASONING_EFFORT,
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
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            body = json.load(response)
            elapsed_ms = round((time.monotonic() - started) * 1000)
            usage = body.get("usage") or {}
            print(f"status={response.status}")
            print(f"requested_alias={MODEL}")
            print(f"model_id={response.headers.get('x-litellm-model-id', 'not-returned')}")
            print(f"response_model={body.get('model', 'not-returned')}")
            print(f"latency_ms={elapsed_ms}")
            print(f"prompt_tokens={usage.get('prompt_tokens', 'not-returned')}")
            print(f"completion_tokens={usage.get('completion_tokens', 'not-returned')}")
            content = body["choices"][0]["message"].get("content") or ""
            print(f"content={content if content else '<empty>'}")
            return 0 if content.strip() == EXPECTED_TEXT else 1
    except urllib.error.HTTPError as exc:
        print(f"provider test failed: HTTP {exc.code}", file=sys.stderr)
        return 1
    except (OSError, KeyError, ValueError) as exc:
        print(f"provider test failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
