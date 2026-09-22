# Portfolio evidence checklist

Only publish evidence from a controlled environment. Every screenshot should show a timestamp or revision identifier where practical and must be inspected before upload.

| Evidence | Show | Hide or redact |
| --- | --- | --- |
| Architecture | Mermaid diagram and component boundaries | Nothing sensitive should exist |
| LiteLLM dashboard | Healthy gateway, model aliases, aggregate usage | Keys, users, prompts, internal URLs |
| OpenAI primary | `general-chat` request, success status, `openai-primary` route evidence | Authorization header, full sensitive prompt |
| Gemini direct | `gemini-direct` request and `gemini-fallback` route evidence | Provider key, raw headers |
| Controlled fallback | Primary 429/503 stub, fallback route ID, successful response | Credentials and internal addresses |
| Sanitized logs | Request ID, alias, provider, status, latency, fallback attempt | Tokens, cookies, prompts, user data |
| Langfuse trace | Correlated trace, provider/model, latency, token/cost fields | Langfuse keys, private content, user identifiers |
| PostgreSQL persistence | Aggregate/key alias data surviving gateway restart | Connection URL, hashes, raw token records |
| Cloud Run | Ready revision, traffic allocation, health result | Project IDs if private, environment values, secrets |
| CI | Passing unit/config/secret/Compose/Docker jobs | Repository secrets and action debug output |

## Capture order

1. CI checks passing.
2. Local Compose services healthy.
3. OpenAI primary request.
4. Gemini direct request.
5. Controlled OpenAI failure followed by Gemini success.
6. Sanitized LiteLLM logs correlated by call ID.
7. Optional Langfuse trace with privacy settings verified.
8. PostgreSQL-backed usage or key persistence.
9. Cloud Run ready revision and health check.
10. Final architecture diagram.

Never publish provider keys, LiteLLM keys, database URLs, secret values, cookies, service-account material, unredacted authorization headers, private network details, or sensitive prompt content.
