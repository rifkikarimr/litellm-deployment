# Portfolio evidence checklist

Only publish evidence from a controlled environment. Every screenshot should show a timestamp or commit identifier where practical and must be inspected before upload.

| Evidence | Show | Hide or redact |
| --- | --- | --- |
| Architecture | Portable Compose diagram and component boundaries | Nothing sensitive should exist |
| Docker Compose | Healthy LiteLLM and PostgreSQL services | Environment values and host details |
| LiteLLM dashboard | Healthy gateway, model aliases, aggregate usage | Keys, users, prompts, internal URLs |
| OpenAI primary | `general-chat` request and `openai-primary` route evidence | Authorization header and sensitive prompts |
| Gemini direct | `gemini-direct` request and `gemini-fallback` route evidence | Provider key and raw headers |
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
6. OpenAI primary request.
7. Gemini direct request.
8. Controlled primary failure followed by Gemini success.
9. Sanitized LiteLLM logs correlated by request ID.
10. Optional Langfuse trace with privacy settings verified.
11. Final portable architecture diagram.

Never publish provider keys, LiteLLM keys, database URLs, secret values, cookies, authorization headers, private network details, host access details, or sensitive prompt content.
