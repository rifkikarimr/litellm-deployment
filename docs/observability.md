# Observability

## Default signals

The gateway writes structured JSON logs to stdout/stderr for container-native collection. PostgreSQL-backed LiteLLM data provides request usage, virtual-key attribution, budgets, model groups, tokens, and cost estimates where LiteLLM has current pricing metadata.

The `model_info.id` values `openai-primary`, `openai-direct`, and `gemini-fallback` make the selected route visible in response headers and logs. Recent LiteLLM spend logs also record original model group and attempted fallback metadata; verify these fields against the pinned release before using them for alerts.

## Langfuse

`config.yaml` uses LiteLLM's native `langfuse_otel` callback. No custom callback mutates payloads or copies authentication metadata.

To enable export, set:

```env
LITELLM_OTEL_V2=true
LANGFUSE_PUBLIC_KEY=replace-me
LANGFUSE_SECRET_KEY=replace-me
LANGFUSE_HOST=https://cloud.langfuse.com
OTEL_INSTRUMENTATION_GENAI_CAPTURE_MESSAGE_CONTENT=no_content
```

For self-hosted Langfuse, replace `LANGFUSE_HOST` with the HTTPS base URL reachable from the gateway. Core routing and PostgreSQL do not depend on Langfuse availability, but operators should test callback failure behavior before production rollout.

## Trace correlation

Capture the LiteLLM call ID from response headers, then correlate it with JSON logs and Langfuse spans. Useful fields include:

- requested model group (`general-chat`);
- resolved model/deployment identifier;
- provider;
- status and exception class;
- latency;
- prompt, completion, and total token counts;
- cost estimate;
- original model group and fallback attempts, when emitted by the pinned version.

## Privacy

LiteLLM OTel v2 defaults to metadata-only spans and does not capture prompts or responses. Keep that default unless a reviewed use case requires content. If content capture is enabled, LLM observability can transmit prompts, outputs, user identifiers, tool arguments, and metadata. Before enabling it:

- determine whether prompt/response capture is permitted;
- redact or avoid personal, regulated, and secret data;
- restrict project access and retention;
- use TLS for self-hosted endpoints;
- test deletion and incident-response procedures.

If payload capture is not acceptable, configure the supported LiteLLM/Langfuse content-suppression controls for the pinned version and verify the resulting trace before handling real data.
