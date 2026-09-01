#!/usr/bin/env python3
import json
import os
import ssl
import sys
import textwrap
import urllib.error
import urllib.request
from datetime import datetime, timezone


BASE_URL = os.getenv(
    "LITELLM_BASE_URL",
    "https://litellm-rnd-890434106746.asia-southeast2.run.app",
).rstrip("/")
API_KEY = os.getenv("LITELLM_API_KEY")
MODEL = os.getenv("LITELLM_MODEL", "model-b")
TIMEOUT_SECONDS = int(os.getenv("LITELLM_TIMEOUT_SECONDS", "120"))
SKIP_SSL_VERIFY = os.getenv("LITELLM_SKIP_SSL_VERIFY", "").lower() in {"1", "true", "yes"}


def build_payload() -> dict:
    now_iso = datetime.now(timezone.utc).isoformat()

    system_prompt = textwrap.dedent(
        """
        You are a senior strategy analyst supporting an executive team.
        Produce an answer that is rigorous, concise, and operationally useful.
        Follow these rules:
        1. Think through tradeoffs before concluding.
        2. State assumptions explicitly.
        3. Distinguish facts, risks, and recommendations.
        4. Return valid JSON only.
        5. Use this schema exactly:
           {
             "executive_summary": string,
             "assumptions": [string],
             "key_risks": [{"risk": string, "severity": "low" | "medium" | "high", "mitigation": string}],
             "prioritized_actions": [{"priority": integer, "action": string, "owner": string, "deadline": string}],
             "metrics": [{"name": string, "target": string, "why_it_matters": string}]
           }
        """
    ).strip()

    user_prompt = textwrap.dedent(
        f"""
        Scenario:
        A mid-sized logistics company operating in Indonesia plans to roll out an AI customer operations assistant over the next 90 days.
        The assistant will handle shipment-status questions, summarize complaint tickets, and draft incident updates for enterprise clients.

        Constraints:
        - Data includes customer names, phone numbers, shipment IDs, and internal escalation notes.
        - The system will use LiteLLM as the gateway, Vertex AI as the model provider, Langfuse for observability, and PostgreSQL for persistent config.
        - The initial budget ceiling is USD 8,000 for the first quarter.
        - The team consists of 1 product manager, 2 backend engineers, 1 data analyst, and 3 support leads.
        - The rollout must start with a pilot in 2 regions before national scale-up.

        Required output:
        - Recommend the best 30/60/90 day operating approach.
        - Include security, observability, quality control, and business adoption considerations.
        - Include measurable success metrics.
        - Keep it practical for an executive review, not academic.

        Additional context:
        - This request is intentionally used as a Langfuse observability test.
        - Test timestamp: {now_iso}
        """
    ).strip()

    return {
        "model": MODEL,
        "temperature": 0.2,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "metadata": {
            "workflow": "langfuse_test_python",
            "test_type": "complex_prompt",
            "test_timestamp": now_iso,
            "source": "local_test_py",
            "environment": "manual_validation",
            "session_id": f"langfuse-test-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}",
            "tags": ["langfuse", "litellm", "vertex", "complex-prompt"],
        },
    }


def main() -> int:
    if not API_KEY:
        print(
            "Missing LITELLM_API_KEY. Export it first, for example:\n"
            "export LITELLM_API_KEY='<your-litellm-key>'",
            file=sys.stderr,
        )
        return 1

    payload = build_payload()
    body = json.dumps(payload).encode("utf-8")

    request = urllib.request.Request(
        f"{BASE_URL}/v1/chat/completions",
        data=body,
        method="POST",
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {API_KEY}",
            "User-Agent": "litellm-langfuse-test/1.0",
        },
    )

    try:
        ssl_context = None
        if SKIP_SSL_VERIFY:
            ssl_context = ssl._create_unverified_context()

        with urllib.request.urlopen(
            request,
            timeout=TIMEOUT_SECONDS,
            context=ssl_context,
        ) as response:
            response_body = response.read().decode("utf-8")
            parsed = json.loads(response_body)

            print("status:", response.status)
            print("x-litellm-call-id:", response.headers.get("x-litellm-call-id"))
            print("x-litellm-model-group:", response.headers.get("x-litellm-model-group"))
            print("x-litellm-response-duration-ms:", response.headers.get("x-litellm-response-duration-ms"))
            print("response:")
            print(json.dumps(parsed, indent=2))
            return 0
    except urllib.error.HTTPError as exc:
        error_body = exc.read().decode("utf-8", errors="replace")
        print(f"HTTP error: {exc.code}", file=sys.stderr)
        print(error_body, file=sys.stderr)
        return 2
    except Exception as exc:
        print(f"Request failed: {exc}", file=sys.stderr)
        return 3


if __name__ == "__main__":
    raise SystemExit(main())
