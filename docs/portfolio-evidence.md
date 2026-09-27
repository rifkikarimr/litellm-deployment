# Portfolio evidence checklist

Only publish evidence from a controlled environment. Every screenshot should show a timestamp or commit identifier where practical and must be inspected before upload.

| Evidence | Show | Hide or redact |
| --- | --- | --- |
| Architecture | Portable Compose diagram and component boundaries | Nothing sensitive should exist |
| Docker Compose | Healthy LiteLLM and PostgreSQL services | Environment values and host details |
| LiteLLM dashboard | Healthy gateway, model aliases, aggregate usage | Keys, users, prompts, internal URLs |
| Gemini primary | `general-chat` request and `gemini-primary` route evidence | Authorization header and sensitive prompts |
| OpenAI direct | `openai-direct` request and route evidence | Provider key and raw headers |
| Controlled fallback | Primary failure stub, fallback route ID, successful response | Credentials and internal addresses |
| Sanitized logs | Request ID, alias, provider, status, latency, fallback attempt | Tokens, cookies, prompts, user data |
| Langfuse trace | Correlated trace, provider/model, latency, token/cost fields | Langfuse keys, private content, identifiers |
| PostgreSQL persistence | Aggregate usage or key aliases surviving restart | Connection URL, hashes, raw token records |
| Portability | Same Compose config rendered on a second Docker-capable host | Hostnames, addresses, and credentials |
| CI | Passing unit/config/history/Compose/Docker jobs | Repository secrets and debug output |

## Capture order

1. CI checks passing.
2. `docker compose config` and Docker image build.
3. Both Compose services healthy.
4. Gateway health check.
5. PostgreSQL-backed data surviving `make restart`.
6. Gemini primary request.
7. OpenAI direct request.
8. Controlled Gemini failure followed by OpenAI success.
9. Sanitized LiteLLM logs correlated by request ID.
10. Optional Langfuse trace with privacy settings verified.
11. Final portable architecture diagram.

Never publish provider keys, LiteLLM keys, database URLs, secret values, cookies, authorization headers, private network details, host access details, or sensitive prompt content.

## Validated live evidence — 2026-09-26

The following results were captured on the local Docker Compose deployment with
LiteLLM 1.100.1. They are point-in-time validation, not an availability SLA.

| Case | Result | Safe evidence |
| --- | --- | --- |
| Gemini direct | PASS | HTTP 200, route `gemini-direct`, 3.776 s, 9 prompt tokens, 4 completion tokens, `GEMINI_OK` |
| OpenAI direct | PASS | HTTP 200, route `openai-direct`, 2.593 s, 13 prompt tokens, 6 completion tokens, `OPENAI_OK` |
| Normal public route | PASS | HTTP 200, alias `general-chat`, route `gemini-primary`, 2.388 s, `PRIMARY_OK` |
| Controlled fallback | PASS | Gemini adapter received three loopback HTTP 500 attempts; OpenAI fallback returned successfully |
| Streaming | PASS | HTTP 200, route `gemini-primary`, 3 SSE chunks, 1.646 s, `STREAM_OK` |
| Runtime logs | PASS | Configured secret values and common API-key/database-URL patterns were not detected |

One initial Gemini direct request returned HTTP 200 but no visible content because
the 16-token output limit was consumed by reasoning. The successful retry used
reasoning effort `low` and a 32-token limit. Count both requests in cost records.

No screenshots were captured in this validation run. If screenshots are added,
redact authorization headers, API keys, master/salt keys, database credentials,
provider account identifiers, and unrelated host details.
