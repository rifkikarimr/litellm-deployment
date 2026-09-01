#!/usr/bin/env python3
import argparse
import json
import os
import ssl
import sys
import textwrap
import urllib.error
import urllib.request
from datetime import datetime, timezone


DEFAULT_BASE_URL = "https://litellm-rnd-890434106746.asia-southeast2.run.app"
DEFAULT_MODEL = "gemini-3.1-flash-lite"
DEFAULT_TIMEOUT_SECONDS = 120


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Send a Vertex AI model request through LiteLLM."
    )
    parser.add_argument(
        "--model",
        default=os.getenv("LITELLM_MODEL", DEFAULT_MODEL),
        help="LiteLLM model alias to call.",
    )
    parser.add_argument(
        "--base-url",
        default=os.getenv("LITELLM_BASE_URL", DEFAULT_BASE_URL).rstrip("/"),
        help="LiteLLM base URL.",
    )
    parser.add_argument(
        "--api-key",
        default=os.getenv("LITELLM_API_KEY"),
        help="LiteLLM API key. Falls back to LITELLM_API_KEY env var.",
    )
    parser.add_argument(
        "--prompt",
        default=os.getenv(
            "VERTEX_TEST_PROMPT",
            "Reply with a two-sentence summary of why this model is useful for production testing.",
        ),
        help="User prompt to send.",
    )
    parser.add_argument(
        "--system",
        default=os.getenv(
            "VERTEX_TEST_SYSTEM_PROMPT",
            "You are a concise AI platform validation assistant. Answer directly.",
        ),
        help="Optional system prompt.",
    )
    parser.add_argument(
        "--temperature",
        type=float,
        default=float(os.getenv("VERTEX_TEST_TEMPERATURE", "0.2")),
        help="Sampling temperature.",
    )
    parser.add_argument(
        "--max-tokens",
        type=int,
        default=int(os.getenv("VERTEX_TEST_MAX_TOKENS", "256")),
        help="Max completion tokens.",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=int(os.getenv("LITELLM_TIMEOUT_SECONDS", str(DEFAULT_TIMEOUT_SECONDS))),
        help="HTTP timeout in seconds.",
    )
    parser.add_argument(
        "--skip-ssl-verify",
        action="store_true",
        default=os.getenv("LITELLM_SKIP_SSL_VERIFY", "").lower() in {"1", "true", "yes"},
        help="Disable TLS certificate verification.",
    )
    parser.add_argument(
        "--complex",
        action="store_true",
        help="Use a more complex executive-planning prompt instead of --prompt.",
    )
    return parser.parse_args()


def build_complex_prompt() -> tuple[str, str]:
    now_iso = datetime.now(timezone.utc).isoformat()
    system_prompt = textwrap.dedent(
        """
        You are a senior strategy analyst supporting an executive team.
        Produce an answer that is rigorous, concise, and operationally useful.
        Distinguish facts, risks, and recommendations.
        Return valid JSON only.
        """
    ).strip()
    user_prompt = textwrap.dedent(
        f"""
        Scenario:
        A regional logistics company will deploy an AI operations assistant in 90 days.
        The system uses LiteLLM as the gateway, Vertex AI as the model provider, Langfuse for observability, and PostgreSQL for config storage.

        Constraints:
        - Budget ceiling: USD 8,000 for the first quarter
        - Team: 1 PM, 2 backend engineers, 1 analyst, 3 support leads
        - Rollout starts in 2 regions before national scale
        - Data contains customer PII and shipment identifiers

        Required output:
        - Recommend a practical 30/60/90 day rollout plan
        - Include security, observability, quality, and adoption concerns
        - Include measurable metrics

        Test timestamp: {now_iso}
        """
    ).strip()
    return system_prompt, user_prompt


def build_payload(args: argparse.Namespace) -> dict:
    now_iso = datetime.now(timezone.utc).isoformat()
    system_prompt = args.system
    user_prompt = args.prompt

    if args.complex:
        system_prompt, user_prompt = build_complex_prompt()

    return {
        "model": args.model,
        "temperature": args.temperature,
        "max_tokens": args.max_tokens,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "metadata": {
            "workflow": "vertex_test_python",
            "test_type": "complex_prompt" if args.complex else "simple_prompt",
            "test_timestamp": now_iso,
            "source": "vertex_test.py",
            "environment": "manual_validation",
            "session_id": f"vertex-test-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}",
            "tags": ["vertex", "litellm", args.model],
        },
    }


def main() -> int:
    args = parse_args()
    if not args.api_key:
        print(
            "Missing LiteLLM API key. Set LITELLM_API_KEY or pass --api-key.",
            file=sys.stderr,
        )
        return 1

    payload = build_payload(args)
    body = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        f"{args.base_url}/v1/chat/completions",
        data=body,
        method="POST",
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {args.api_key}",
            "User-Agent": "vertex-test/1.0",
        },
    )

    ssl_context = None
    if args.skip_ssl_verify:
        ssl_context = ssl._create_unverified_context()

    try:
        with urllib.request.urlopen(
            request,
            timeout=args.timeout,
            context=ssl_context,
        ) as response:
            parsed = json.loads(response.read().decode("utf-8"))
            print("status:", response.status)
            print("x-litellm-call-id:", response.headers.get("x-litellm-call-id"))
            print("x-litellm-model-group:", response.headers.get("x-litellm-model-group"))
            print("x-litellm-response-duration-ms:", response.headers.get("x-litellm-response-duration-ms"))
            print("response:")
            print(json.dumps(parsed, indent=2))
            return 0
    except urllib.error.HTTPError as exc:
        print(f"HTTP error: {exc.code}", file=sys.stderr)
        print(exc.read().decode("utf-8", errors="replace"), file=sys.stderr)
        return 2
    except Exception as exc:
        print(f"Request failed: {exc}", file=sys.stderr)
        return 3


if __name__ == "__main__":
    raise SystemExit(main())
