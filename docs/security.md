# Security

## Repository controls

- `.env`, private keys, credential files, browser captures, and Python artifacts are ignored.
- `.env.example` contains placeholders only.
- `config.yaml` reads every credential from the environment.
- `scripts/scan_secrets.py` rejects common API-key formats, private-key material, private IPv4 addresses, service-account fields, and stale corporate identifiers.
- `make validate` scans both the current tree and every unique blob reachable from local Git refs.
- CI checks out full history and runs the same scans on every pull request.

If a real secret was ever committed, deleting the current file is insufficient: rotate it and purge history according to the hosting provider's guidance.

## Runtime controls

- Use LiteLLM virtual keys for applications and reserve the master key for administration.
- Give each workload a separate key, model allowlist, budget, and rate limit.
- Keep `LITELLM_SALT_KEY` stable and secret for persisted encrypted values.
- PostgreSQL is private to the Compose network and has no host port mapping.
- The gateway binds to loopback by default.
- Require a TLS reverse proxy, authentication, and host firewall rules before allowing network clients.
- Send logs to access-controlled storage and avoid debug logging for real workloads.
- Back up PostgreSQL with database-aware tools and test restoration.

## Runtime secrets

Provide these values through an untracked `.env` file or the secret-injection mechanism available on the Docker host:

- `OPENAI_API_KEY`
- `GEMINI_API_KEY`
- `LITELLM_MASTER_KEY`
- `LITELLM_SALT_KEY`
- `POSTGRES_PASSWORD`
- `DATABASE_URL`
- `LANGFUSE_PUBLIC_KEY` and `LANGFUSE_SECRET_KEY` when observability is enabled

Restrict `.env` file permissions and access to the Docker daemon. Never bake credentials into the image, commit them, pass them as build arguments, or publish them through screenshots and logs. Model identifiers and a non-secret Langfuse host may remain ordinary environment variables.

## Host security boundary

Anyone with control of the Docker daemon can normally inspect container configuration, mount data, and access the database volume. Treat Docker administrator access as privileged access to the gateway and its secrets. Keep the host patched, restrict interactive access, and avoid mounting the Docker socket into application containers.

## Data handling

Prompts and outputs may contain sensitive information. Provider and observability data retention, regional processing, training defaults, and subprocessors remain operator decisions. Complete a data-flow review before using production data.
