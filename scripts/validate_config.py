#!/usr/bin/env python3
"""Validate the static LiteLLM configuration without provider credentials."""

from pathlib import Path
import sys

import yaml


ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / "config.yaml"
VERSION_PATH = ROOT / ".litellm-version"
DOCKERFILE_PATH = ROOT / "Dockerfile"


def fail(message: str) -> None:
    raise AssertionError(message)


def main() -> int:
    config = yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8"))
    if not isinstance(config, dict):
        fail("config.yaml must contain a mapping")

    models = config.get("model_list")
    if not isinstance(models, list):
        fail("model_list must be a list")

    by_name = {entry["model_name"]: entry for entry in models}
    required_aliases = {"general-chat", "openai-direct", "gemini-direct"}
    if set(by_name) != required_aliases:
        fail(f"expected aliases {sorted(required_aliases)}, got {sorted(by_name)}")

    primary = by_name["general-chat"]["litellm_params"]
    fallback = by_name["gemini-direct"]["litellm_params"]
    if primary.get("model") != "os.environ/PRIMARY_MODEL":
        fail("general-chat must read PRIMARY_MODEL from the environment")
    if primary.get("api_key") != "os.environ/OPENAI_API_KEY":
        fail("general-chat must read OPENAI_API_KEY from the environment")
    if fallback.get("model") != "os.environ/FALLBACK_MODEL":
        fail("gemini-direct must read FALLBACK_MODEL from the environment")
    if fallback.get("api_key") != "os.environ/GEMINI_API_KEY":
        fail("gemini-direct must read GEMINI_API_KEY from the environment")

    router = config.get("router_settings", {})
    if router.get("fallbacks") != [{"general-chat": ["gemini-direct"]}]:
        fail("general-chat must fall back only to gemini-direct")
    if not 0 <= int(router.get("num_retries", -1)) <= 3:
        fail("num_retries must remain bounded between 0 and 3")

    retry_policy = router.get("retry_policy", {})
    for name in (
        "AuthenticationErrorRetries",
        "BadRequestErrorRetries",
        "ContentPolicyViolationErrorRetries",
    ):
        if retry_policy.get(name) != 0:
            fail(f"{name} must fail fast")

    version = VERSION_PATH.read_text(encoding="utf-8").strip()
    dockerfile = DOCKERFILE_PATH.read_text(encoding="utf-8")
    if f"ARG LITELLM_VERSION={version}" not in dockerfile:
        fail("Dockerfile and .litellm-version are out of sync")

    print("config validation: PASS")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (AssertionError, KeyError, TypeError, ValueError, yaml.YAMLError) as exc:
        print(f"config validation: FAIL: {exc}", file=sys.stderr)
        raise SystemExit(1)
