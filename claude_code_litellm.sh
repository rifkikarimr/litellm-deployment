#!/usr/bin/env bash
set -euo pipefail

if ! command -v claude >/dev/null 2>&1; then
  echo "claude command not found. Install Claude Code first." >&2
  exit 1
fi

keychain_service="${LITELLM_KEYCHAIN_SERVICE:-litellm-claude-code}"
api_key="${LITELLM_API_KEY:-${ANTHROPIC_API_KEY:-}}"
if [[ -z "$api_key" ]] && command -v security >/dev/null 2>&1; then
  api_key="$(security find-generic-password -s "$keychain_service" -w 2>/dev/null || true)"
fi

if [[ -z "$api_key" ]]; then
  echo "Missing LITELLM_API_KEY / ANTHROPIC_API_KEY and no macOS Keychain item named '$keychain_service' was found." >&2
  exit 1
fi

export LITELLM_API_KEY="$api_key"
export ANTHROPIC_BASE_URL="${LITELLM_BASE_URL:-https://litellm-rnd-890434106746.asia-southeast2.run.app}"
export ANTHROPIC_API_KEY="$api_key"
unset ANTHROPIC_AUTH_TOKEN

# Claude Code is speaking Anthropic Messages format to LiteLLM, but LiteLLM
# is routing to Vertex-backed Claude models. Disable experimental betas to avoid
# feature/header mismatches on this gateway path.
export CLAUDE_CODE_DISABLE_EXPERIMENTAL_BETAS="${CLAUDE_CODE_DISABLE_EXPERIMENTAL_BETAS:-1}"

# Force Claude Code off the machine's direct Vertex provider path and onto the
# Anthropic-compatible LiteLLM gateway.
export CLAUDE_CODE_USE_VERTEX=0
unset ANTHROPIC_VERTEX_PROJECT_ID
unset CLOUD_ML_REGION

# Keep Claude Code pinned to the Opus alias by default. With an Opus-only
# LiteLLM key, Claude Code can otherwise attempt a Sonnet path implicitly.
default_opus_model="${ANTHROPIC_DEFAULT_OPUS_MODEL:-claude-opus-4-7}"
export ANTHROPIC_DEFAULT_OPUS_MODEL="$default_opus_model"
export ANTHROPIC_DEFAULT_SONNET_MODEL="${ANTHROPIC_DEFAULT_SONNET_MODEL:-$default_opus_model}"

default_model="${CLAUDE_CODE_MODEL:-$ANTHROPIC_DEFAULT_OPUS_MODEL}"

extra_args=()
has_setting_sources=false
has_model=false

for arg in "$@"; do
  case "$arg" in
    --setting-sources|--setting-sources=*)
      has_setting_sources=true
      ;;
    --model|--model=*)
      has_model=true
      ;;
  esac
done

if [[ "$has_setting_sources" == false ]]; then
  # Skip ~/.claude/settings.json so a user-level Vertex configuration cannot
  # silently bypass LiteLLM.
  extra_args+=(--setting-sources project,local)
fi

if [[ "$has_model" == false ]]; then
  extra_args+=(--model "$default_model")
fi

exec claude "${extra_args[@]}" "$@"
