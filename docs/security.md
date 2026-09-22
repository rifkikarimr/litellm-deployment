# Security

## Repository controls

- `.env`, private keys, service-account files, browser captures, and Python artifacts are ignored.
- `.env.example` contains placeholders only.
- `config.yaml` reads every credential from the environment.
- `scripts/scan_secrets.py` rejects common API-key formats, private-key material, private IPv4 addresses, service-account fields, and the removed corporate identifier.
- `make validate` scans both the current tree and every unique blob reachable from local Git refs.
- CI checks out full history and runs the same scans on every pull request.

If a real secret was ever committed, deleting the current file is insufficient: rotate it and purge history according to the hosting provider's guidance.

## Runtime controls

- Use LiteLLM virtual keys for applications and reserve the master key for administration.
- Give each workload a separate key, model allowlist, budget, and rate limit.
- Keep `LITELLM_SALT_KEY` stable and secret for persisted encrypted values.
- Use a least-privilege database user and require TLS for non-local database traffic.
- Do not expose PostgreSQL publicly. The local Compose service is network-only.
- Restrict Cloud Run ingress or add an identity-aware control when the service is not intentionally public.
- Send logs to access-controlled storage and avoid debug logging in production.

## Secret Manager on Cloud Run

Store these values as separate Google Secret Manager secrets and map them to runtime environment variables:

- `OPENAI_API_KEY`
- `GEMINI_API_KEY`
- `LITELLM_MASTER_KEY`
- `LITELLM_SALT_KEY`
- `DATABASE_URL`
- `LANGFUSE_PUBLIC_KEY` and `LANGFUSE_SECRET_KEY` when observability is enabled

Grant the Cloud Run service account access only to the required secret versions. Prefer rotation and version pinning procedures that allow rollback.

Model identifiers and a non-secret Langfuse host can be ordinary environment variables. Never bake credentials into the image or pass them as Docker build arguments.

## Data handling

Prompts and outputs may contain sensitive information. Provider and observability data retention, regional processing, training defaults, and subprocessors are deployment decisions outside this repository. Complete a data-flow review before using production data.
