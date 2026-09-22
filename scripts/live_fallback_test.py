#!/usr/bin/env python3
"""Opt-in paid test: inject an OpenAI 500 and make one real Gemini fallback call."""

from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import os
import threading

import litellm
from litellm import Router


class ForcedFailureHandler(BaseHTTPRequestHandler):
    attempts = 0

    def do_POST(self) -> None:  # noqa: N802 - stdlib handler API
        type(self).attempts += 1
        body = b'{"error":{"message":"controlled primary failure","type":"server_error"}}'
        self.send_response(500)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format: str, *args: object) -> None:
        return


def main() -> int:
    if os.getenv("RUN_PAID_PROVIDER_TESTS") != "1":
        print("Set RUN_PAID_PROVIDER_TESTS=1 to confirm this paid provider test.")
        return 2
    gemini_key = os.getenv("GEMINI_API_KEY")
    if not gemini_key:
        print("Set GEMINI_API_KEY before running this opt-in paid test.")
        return 2
    if gemini_key == "replace-me":
        print("Replace the GEMINI_API_KEY placeholder before running this test.")
        return 2

    litellm.suppress_debug_info = True

    primary_model = os.getenv("PRIMARY_MODEL", "openai/gpt-5.6-luna")
    fallback_model = os.getenv("FALLBACK_MODEL", "gemini/gemini-3.7-flash")

    server = ThreadingHTTPServer(("127.0.0.1", 0), ForcedFailureHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        router = Router(
            model_list=[
                {
                    "model_name": "general-chat",
                    "litellm_params": {
                        "model": primary_model,
                        "api_key": "controlled-test-placeholder",
                        "api_base": f"http://127.0.0.1:{server.server_port}/v1",
                    },
                },
                {
                    "model_name": "gemini-direct",
                    "litellm_params": {
                        "model": fallback_model,
                        "api_key": gemini_key,
                        "additional_drop_params": ["temperature", "top_p", "top_k"],
                    },
                },
            ],
            fallbacks=[{"general-chat": ["gemini-direct"]}],
            num_retries=0,
            timeout=30,
        )
        try:
            response = router.completion(
                model="general-chat",
                messages=[{"role": "user", "content": "Reply with exactly: ready"}],
                max_tokens=32,
            )
        except Exception as exc:
            print(f"fallback test failed: {type(exc).__name__}")
            return 1
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)

    if ForcedFailureHandler.attempts < 1:
        print("fallback test failed: controlled primary was not attempted")
        return 1

    print("primary_failure_injected=true")
    print("fallback_completed=true")
    print(f"response_model={getattr(response, 'model', 'not-returned')}")
    print(f"content={response.choices[0].message.content}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
