#!/usr/bin/env python3
"""Run an explicitly requested paid-provider integration test through LiteLLM."""

import json
import os
import sys
import urllib.error
import urllib.request


BASE_URL = os.getenv("LITELLM_BASE_URL", "http://127.0.0.1:4000").rstrip("/")
API_KEY = os.getenv("LITELLM_API_KEY") or os.getenv("LITELLM_MASTER_KEY")
MODEL = os.getenv("LITELLM_MODEL", "general-chat")


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
        "messages": [{"role": "user", "content": "Reply with exactly: ready"}],
        "max_tokens": 32,
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
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            body = json.load(response)
            print(f"status={response.status}")
            print(f"requested_alias={MODEL}")
            print(f"model_id={response.headers.get('x-litellm-model-id', 'not-returned')}")
            print(f"response_model={body.get('model', 'not-returned')}")
            print(f"content={body['choices'][0]['message']['content']}")
            return 0
    except urllib.error.HTTPError as exc:
        print(f"provider test failed: HTTP {exc.code}", file=sys.stderr)
        return 1
    except (OSError, KeyError, ValueError) as exc:
        print(f"provider test failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
