# LiteLLM on Cloud Run (R&D) + PostgreSQL on GCE (Docker)

This repo documents an R&D setup where **LiteLLM Proxy + Web UI** runs on **Google Cloud Run** (public), while **PostgreSQL** runs on a **GCE VM** via Docker. Cloud Run reaches private resources (Postgres and self-hosted Langfuse) over VPC networking.

## Architecture

- **Cloud Run (public ingress):** LiteLLM Proxy + UI
- **GCE VM #1 (private IP):** PostgreSQL (Docker Compose)
- **GCE VM #2 (private IP):** Langfuse (self-hosted)
- **Networking:** Cloud Run -> VPC/Subnet -> VM private IPs (Direct VPC egress)
- **Secrets:** Secret Manager -> Cloud Run environment variables

## Key concepts

- Cloud Run containers must listen on `PORT` and bind to `0.0.0.0`.
- LiteLLM default port is `4000`, but can be overridden via `--port` and `--host`.
- `config.yaml` already enables Langfuse callback with `callbacks: ["langfuse_otel"]`.
- For this callback, set `LANGFUSE_PUBLIC_KEY`, `LANGFUSE_SECRET_KEY`, and `LANGFUSE_OTEL_HOST`.
- Vertex AI models in `config.yaml` use the `vertex_ai/` route from LiteLLM and read `VERTEX_PROJECT_ID` and `VERTEX_LOCATION` from environment variables.
- If you want to authenticate Vertex AI with a service account JSON key, set `GOOGLE_APPLICATION_CREDENTIALS` to the mounted file path at runtime.

## Repository contents

- `Dockerfile` - LiteLLM container image
- `config.yaml` - LiteLLM proxy config (models + DB + callbacks)
- `docker-compose-pg.yaml` - PostgreSQL container config for the VM
- `pg_hba.conf` - Postgres host-based auth rules
- `schema.prisma` - Prisma schema used by LiteLLM proxy
- `Makefile` - LiteLLM schema sync + Prisma reconcile helper

> Do not commit secrets (`.env`, DB passwords, master keys, Langfuse keys). Use Secret Manager.

## Env reference (local/dev)

Use strict `.env` formatting:

- No spaces around `=`
- No wrapping values with quotes unless required by the parser you use
- Avoid empty `UI_PASSWORD`

Example:

```env
DATABASE_URL=postgresql://REDACTED
LITELLM_MASTER_KEY=<master_key>
LITELLM_SALT_KEY=<salt_key>

UI_USERNAME=admin
UI_PASSWORD=<strong_password>

STORE_MODEL_IN_DB=True

VERTEX_PROJECT_ID=example-project
VERTEX_LOCATION=global
GOOGLE_APPLICATION_CREDENTIALS=/absolute/path/to/example-project-882129d7cb18.json

LANGFUSE_PUBLIC_KEY=<langfuse_public_key>
LANGFUSE_SECRET_KEY=<langfuse_secret_key>
LANGFUSE_OTEL_HOST=http://192.0.2.10:3000

# Optional for self-hosted OTEL setups
OTEL_EXPORTER_OTLP_PROTOCOL=http/protobuf
OTEL_EXPORTER_OTLP_TRACES_ENDPOINT=http://192.0.2.10:3000/api/public/otel/v1/traces
```

## Deployment summary

### 1) PostgreSQL (GCE VM, Docker Compose)

- Run Postgres on a VM private IP.
- Ensure Postgres listens externally and host-based auth allows Cloud Run subnet (via `pg_hba.conf`).
- Keep DB user naming consistent across files:
  - `docker-compose-pg.yaml`: `POSTGRES_USER: litellm-user`
  - `DATABASE_URL`: `litellm-user`
  - `pg_hba.conf`: `host litellm litellm-user ...`

### 2) Secrets (Secret Manager)

Create these secrets (example names):

- `DATABASE_URL_LLM`
- `LITELLM_MASTER_KEY`
- `LITELLM_SALT_KEY`
- `UI_USERNAME`
- `UI_PASSWORD`
- `VERTEX_AI_SERVICE_ACCOUNT_JSON`
- `LANGFUSE_PUBLIC_KEY`
- `LANGFUSE_SECRET_KEY`

Optional:

- `LANGFUSE_OTEL_HOST`

Before updating Cloud Run, ensure the Langfuse secrets exist in the same project and have at least one enabled version:

```bash
gcloud config set project <PROJECT_ID>

gcloud secrets describe LANGFUSE_PUBLIC_KEY || gcloud secrets create LANGFUSE_PUBLIC_KEY --replication-policy=automatic
gcloud secrets describe LANGFUSE_SECRET_KEY || gcloud secrets create LANGFUSE_SECRET_KEY --replication-policy=automatic

printf '%s' '<langfuse_public_key>' | gcloud secrets versions add LANGFUSE_PUBLIC_KEY --data-file=-
printf '%s' '<langfuse_secret_key>' | gcloud secrets versions add LANGFUSE_SECRET_KEY --data-file=-

gcloud secrets versions list LANGFUSE_PUBLIC_KEY
gcloud secrets versions list LANGFUSE_SECRET_KEY
```

Notes:

- Use `printf`, not `echo`, when adding secret versions. `echo` often adds a trailing newline, which breaks Langfuse OTEL auth and results in `Failed to export span batch code: 401`.
- Secret payloads must be the raw key values only. Do not include quotes, spaces, or `KEY=` prefixes inside Secret Manager.
- For a JSON secret, upload the file bytes directly:

```bash
gcloud secrets describe VERTEX_AI_SERVICE_ACCOUNT_JSON || gcloud secrets create VERTEX_AI_SERVICE_ACCOUNT_JSON --replication-policy=automatic
gcloud secrets versions add VERTEX_AI_SERVICE_ACCOUNT_JSON \
  --data-file=/Users/rifki.ramadhan/Downloads/example-project-882129d7cb18.json
```

The supplied key file in this workspace resolves to:

- `project_id`: `example-project`
- `client_email`: `litellm-sa@example-project.iam.gserviceaccount.com`

### 3) LiteLLM (Cloud Run)

Map secrets and env vars to the running service.

Example command:

```bash
gcloud run services update litellm-rnd \
  --region=asia-southeast2 \
  --set-secrets=DATABASE_URL=DATABASE_URL_LLM:latest,LITELLM_MASTER_KEY=LITELLM_MASTER_KEY:latest,LITELLM_SALT_KEY=LITELLM_SALT_KEY:latest,UI_USERNAME=UI_USERNAME:latest,UI_PASSWORD=UI_PASSWORD:latest,LANGFUSE_PUBLIC_KEY=LANGFUSE_PUBLIC_KEY:latest,LANGFUSE_SECRET_KEY=LANGFUSE_SECRET_KEY:latest \
  --update-secrets=/secrets/vertex/service-account.json=VERTEX_AI_SERVICE_ACCOUNT_JSON:latest \
  --no-cpu-throttling \
  --set-env-vars=GOOGLE_APPLICATION_CREDENTIALS=/secrets/vertex/service-account.json,VERTEX_PROJECT_ID=example-project,VERTEX_LOCATION=global,LANGFUSE_OTEL_HOST=http://192.0.2.10:3000,STORE_MODEL_IN_DB=True,OTEL_EXPORTER_OTLP_PROTOCOL=http/protobuf,OTEL_EXPORTER_OTLP_TRACES_ENDPOINT=http://192.0.2.10:3000/api/public/otel/v1/traces,OTEL_BSP_SCHEDULE_DELAY=200,OTEL_BSP_MAX_EXPORT_BATCH_SIZE=1
```

Notes:

- Secret name can be `DATABASE_URL_LLM`, but runtime env var must be `DATABASE_URL` because `config.yaml` reads `os.environ/DATABASE_URL`.
- `config.yaml` now reads Vertex routing from `VERTEX_PROJECT_ID` and `VERTEX_LOCATION`, and maps multiple aliases to Vertex AI models:
  - `model-a` -> `vertex_ai/gemini-2.5-pro`
  - `model-b` -> `vertex_ai/gemini-3.7-flash`
  - `gemini-2.5-pro`
  - `gemini-2.5-flash`
  - `gemini-2.5-flash-lite`
  - `gemini-3.1-pro` -> `vertex_ai/gemini-3.1-pro-preview`
  - `gemini-3-flash` -> `vertex_ai/gemini-3-flash-preview`
  - `gemini-3.1-flash-lite` -> `vertex_ai/gemini-3.1-flash-lite-preview`
- `GOOGLE_APPLICATION_CREDENTIALS` should point to the mounted secret file when you use a JSON key. Do not bake the JSON file into the container image.
- For self-hosted Langfuse, do not use `LANGFUSE_BASE_URL`; use `LANGFUSE_OTEL_HOST` for `langfuse_otel` callback.
- Ensure Cloud Run has network path to `192.0.2.10:3000` and `192.0.2.10:5432`.
- Ensure the Cloud Run service account has provider access for your models. For Vertex AI, grant at least `roles/aiplatform.user`.
- For Cloud Run, disable CPU throttling and use a short OTEL batch delay so spans flush reliably after each request.
- As of September 1, 2026, Vertex AI documents `gemini-3.7-flash` as the latest GA Gemini Flash model, available in `global`, `us`, and `eu`.

### 3a) Vertex AI local run

If you want to run LiteLLM locally with the same Vertex AI service account JSON:

```bash
export VERTEX_PROJECT_ID=example-project
export VERTEX_LOCATION=global
export GOOGLE_APPLICATION_CREDENTIALS=/Users/rifki.ramadhan/Downloads/example-project-882129d7cb18.json

litellm --config /Users/rifki.ramadhan/Documents/code/litellm-deployment/config.yaml \
  --host 0.0.0.0 \
  --port 4000
```

Then call LiteLLM with any configured alias, for example:

```bash
curl -sS http://127.0.0.1:4000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <LITELLM_MASTER_KEY>" \
  --data '{"model":"gemini-3.1-flash-lite","messages":[{"role":"user","content":"reply with the word ready"}]}'
```

### 3b) Vertex AI monitoring expectations

With this setup:

- LiteLLM tracks model selection, request volume, spend, and token usage per virtual key / user / team in its own database and UI.
- Langfuse continues to trace full request/response behavior through the LiteLLM callback.
- Vertex AI still receives the requests under the `example-project` project, so Vertex-side quota and provider usage remain visible there.

This gives you two monitoring layers:

1. LiteLLM / Langfuse for gateway-level observability and multi-tenant cost tracking.
2. Vertex AI / GCP for provider-side quota and platform usage.

### 4) Self-hosted Langfuse blob storage

Langfuse v3 OTEL ingestion stores raw event payloads in S3-compatible blob storage before traces appear in the UI. If this storage is misconfigured, `/api/public/otel/v1/traces` can return `500` and no traces will be created.

For a MinIO-based setup:

- Ensure these are set on the Langfuse web and worker containers:
  - `LANGFUSE_S3_EVENT_UPLOAD_BUCKET`
  - `LANGFUSE_S3_EVENT_UPLOAD_ACCESS_KEY_ID`
  - `LANGFUSE_S3_EVENT_UPLOAD_SECRET_ACCESS_KEY`
  - `LANGFUSE_S3_EVENT_UPLOAD_ENDPOINT`
  - `LANGFUSE_S3_EVENT_UPLOAD_FORCE_PATH_STYLE=true`
- If `docker-compose.yml` uses `${MINIO_ROOT_PASSWORD}`, Docker Compose must be able to interpolate that variable from a `.env` file or the shell environment.
- `env_file: ./langfuse.env` is not enough for `${MINIO_ROOT_PASSWORD}` interpolation inside `docker-compose.yml`.

Minimal fix on the Langfuse VM:

```bash
cd /opt/langfuse
grep '^MINIO_ROOT_PASSWORD=' langfuse.env > .env
docker compose up -d langfuse-web langfuse-worker
```

## Validation

1. Open LiteLLM UI and submit at least one model call.
2. Check Cloud Run logs for callback/export errors:

```bash
gcloud run services logs read litellm-rnd --region=asia-southeast2 --limit=200
```

3. Send a direct LiteLLM test request and confirm it returns `200`:

```bash
curl -sS https://<cloud-run-url>/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <LITELLM_MASTER_KEY>" \
  --data '{"model":"gemini-2.5-flash","messages":[{"role":"user","content":"reply with the word ready"}]}'
```

4. In Langfuse UI, confirm traces/generations appear.
5. In LiteLLM UI, verify model/key data persists (DB works).

## Prisma Reconcile

If the LiteLLM admin UI starts failing after a LiteLLM upgrade with errors like:

```text
Authentication Error, Could not find field at `upsertOneLiteLLM_ObjectPermissionTable.create.mcp_toolsets`
```

the running LiteLLM version is ahead of the checked-in Prisma schema.

This repo now pins LiteLLM with [.litellm-version](/Users/rifki.ramadhan/Documents/code/litellm-deployment/.litellm-version:1) and includes a repair target:

```bash
make prisma-reconcile
```

What it does:

- installs `litellm[proxy]` and `prisma` into a local tools virtualenv
- syncs `schema.prisma` from the pinned LiteLLM package
- validates the schema
- runs `prisma db push`
- regenerates the Prisma client

`DATABASE_URL` is taken from the current shell or from `.env` if present.

## Claude Code via LiteLLM

You can point Claude Code at this deployed LiteLLM gateway and still keep:

- LiteLLM request logs and spend tracking
- Langfuse traces
- Vertex AI provider routing behind LiteLLM

This setup follows LiteLLM's Claude Code gateway pattern using the unified Anthropic-compatible endpoint.

### Supported Claude Code models

These LiteLLM aliases are already registered in [config.yaml](/Users/rifki.ramadhan/Documents/code/litellm-deployment/config.yaml):

- `claude-sonnet-4-6`
- `claude-opus-4-6`
- `claude-opus-4-7`

### Recommended auth model

Use a LiteLLM virtual key, not the master key, when launching Claude Code.

Why:

- virtual keys give per-user or per-team tracking
- virtual keys can be budget-limited or model-limited
- master key gives broad access and collapses tracking into a shared admin credential

### Quickstart

Export a LiteLLM virtual key:

```bash
export LITELLM_API_KEY=<your_litellm_virtual_key>
```

Or store it once in macOS Keychain so the wrapper can reuse it without a shell export:

```bash
security add-generic-password -U -a "$USER" -s litellm-claude-code -w <your_litellm_virtual_key>
```

Launch Claude Code through the wrapper script:

```bash
/Users/rifki.ramadhan/Documents/code/litellm-deployment/claude_code_litellm.sh
```

Use an explicit model at startup:

```bash
/Users/rifki.ramadhan/Documents/code/litellm-deployment/claude_code_litellm.sh --model claude-sonnet-4-6
/Users/rifki.ramadhan/Documents/code/litellm-deployment/claude_code_litellm.sh --model claude-opus-4-6
/Users/rifki.ramadhan/Documents/code/litellm-deployment/claude_code_litellm.sh --model claude-opus-4-7
```

Or in print mode:

```bash
/Users/rifki.ramadhan/Documents/code/litellm-deployment/claude_code_litellm.sh -p --model claude-opus-4-7 "Reply with exactly: ready"
```

Important:

- Current Claude Code on this machine is configured in [~/.claude/settings.json](/Users/rifki.ramadhan/.claude/settings.json:1) with `CLAUDE_CODE_USE_VERTEX=1`, which sends traffic directly to Vertex and bypasses LiteLLM.
- The wrapper avoids that by launching Claude Code with `--setting-sources project,local` and by forcing `CLAUDE_CODE_USE_VERTEX=0`.
- For an Opus-only LiteLLM key, the wrapper now pins both Claude Code default model paths to `claude-opus-4-7` unless you explicitly override `--model`, `CLAUDE_CODE_MODEL`, or `ANTHROPIC_DEFAULT_SONNET_MODEL`.
- If LiteLLM returns `team_model_access_denied` for `claude-opus-4-7`, add `claude-opus-4-7` to the team or virtual key allowed-model list in the LiteLLM admin UI after deploying the updated config.

If you want every `claude` invocation on this Mac to go through LiteLLM, alias the wrapper in your shell profile:

```bash
alias claude="/Users/rifki.ramadhan/Documents/code/litellm-deployment/claude_code_litellm.sh"
```

### What the wrapper sets

The script [claude_code_litellm.sh](/Users/rifki.ramadhan/Documents/code/litellm-deployment/claude_code_litellm.sh) exports:

- `LITELLM_API_KEY` from the shell or macOS Keychain service `litellm-claude-code`
- `ANTHROPIC_BASE_URL=https://litellm-rnd-890434106746.asia-southeast2.run.app`
- `ANTHROPIC_API_KEY=$LITELLM_API_KEY`
- `ANTHROPIC_DEFAULT_SONNET_MODEL=claude-opus-4-7`
- `ANTHROPIC_DEFAULT_OPUS_MODEL=claude-opus-4-7`
- `CLAUDE_CODE_DISABLE_EXPERIMENTAL_BETAS=1`
- `CLAUDE_CODE_USE_VERTEX=0`

The wrapper also:

- unsets `ANTHROPIC_AUTH_TOKEN`, `ANTHROPIC_VERTEX_PROJECT_ID`, and `CLOUD_ML_REGION`
- injects `--setting-sources project,local` unless you explicitly pass `--setting-sources`
- injects `--model <default>` unless you explicitly pass `--model`
- keeps fallback routing on Claude Opus in [config.yaml](/Users/rifki.ramadhan/Documents/code/litellm-deployment/config.yaml) via an internal Opus fallback target, so an Opus-limited key does not need access to any non-Opus alias

Why:

- current Claude Code releases use `ANTHROPIC_API_KEY` for proxy/API-key auth
- `ANTHROPIC_AUTH_TOKEN` is not sufficient for this LiteLLM gateway path on the validated Claude Code build
- skipping user settings prevents a machine-level Vertex configuration from silently overriding the LiteLLM route

You can override the gateway URL if needed:

```bash
export LITELLM_BASE_URL=https://your-other-litellm-url
```

### Why `CLAUDE_CODE_DISABLE_EXPERIMENTAL_BETAS=1`

Claude Code is talking to LiteLLM using the Anthropic Messages format, but LiteLLM is routing the request to Vertex-backed Claude models. Anthropic's gateway docs note that this path may require disabling experimental betas to avoid feature/header mismatches.

### Verified working

Real Claude Code CLI test executed on this machine:

```bash
LITELLM_API_KEY=<your_litellm_virtual_key> \
ANTHROPIC_BASE_URL=https://litellm-rnd-890434106746.asia-southeast2.run.app \
ANTHROPIC_API_KEY=$LITELLM_API_KEY \
CLAUDE_CODE_USE_VERTEX=0 \
CLAUDE_CODE_DISABLE_EXPERIMENTAL_BETAS=1 \
claude --setting-sources project,local -p --model claude-opus-4-7 "Reply with exactly: ready"
```

Result:

- output: `ready`

Direct LiteLLM Anthropic-compatible validation also succeeded:

```bash
curl -sS https://litellm-rnd-890434106746.asia-southeast2.run.app/v1/messages \
  -H "content-type: application/json" \
  -H "x-api-key: <your_litellm_virtual_key>" \
  --data '{"model":"claude-opus-4-7","max_tokens":32,"messages":[{"role":"user","content":"Reply with exactly: ready"}]}'
```

The successful response included `x-litellm-call-id`, confirming the request passed through LiteLLM.

### Tracking expectations

When Claude Code is launched this way:

- LiteLLM logs the request
- LiteLLM tracks tokens and spend for the used LiteLLM key
- Langfuse receives the trace through `langfuse_otel`
- Vertex AI still sees the underlying provider call

If you want better attribution in LiteLLM:

- create one virtual key per user or machine
- set a descriptive key alias such as `claude-code-rifki`
- optionally put that key into Claude Code via your shell profile or an `apiKeyHelper`

### Troubleshooting

- `Model not found`
  - Ensure Claude Code model name matches the LiteLLM alias exactly:
    - `claude-sonnet-4-6`
    - `claude-opus-4-6`
    - `claude-opus-4-7`

- `Authentication error`
  - Ensure `LITELLM_API_KEY` is a valid LiteLLM key
  - Prefer a virtual key over the master key
  - If the key is model-limited, ensure the requested model is allowed by that key

- Claude Code still bypasses LiteLLM and you see direct Vertex auth errors such as `invalid_grant` / `invalid_rapt`
  - Check [~/.claude/settings.json](/Users/rifki.ramadhan/.claude/settings.json:1) for `CLAUDE_CODE_USE_VERTEX=1`
  - Launch through [claude_code_litellm.sh](/Users/rifki.ramadhan/Documents/code/litellm-deployment/claude_code_litellm.sh:1) or pass `--setting-sources project,local`

- Claude Code connects but behaves oddly on Vertex-backed Claude models
  - Keep `CLAUDE_CODE_DISABLE_EXPERIMENTAL_BETAS=1`

- You want Claude Code to use another LiteLLM model alias
  - Anthropic-compatible workflows are safest with the Claude aliases above
  - Non-Claude models through Claude Code are a separate compatibility path and should be tested explicitly

## Troubleshooting notes

- **Cloud Run failed to listen on `PORT=8080`**
  - Ensure startup command includes `--host 0.0.0.0 --port ${PORT:-8080}`.

- **DB authentication failed (`no pg_hba.conf entry` / password auth failed)**
  - Re-check subnet allowlist in `pg_hba.conf`.
  - Re-check DB user consistency (`litellm-user` everywhere).
  - Restart/reload Postgres after editing `pg_hba.conf`.

- **Langfuse has no traces**
  - Verify `LANGFUSE_PUBLIC_KEY` and `LANGFUSE_SECRET_KEY` are set.
  - Verify `LANGFUSE_OTEL_HOST` points to a reachable endpoint from Cloud Run.
  - If you set OTEL endpoint overrides, use `OTEL_EXPORTER_OTLP_TRACES_ENDPOINT=http://<langfuse-host>:3000/api/public/otel/v1/traces`.
  - Confirm requests are sent through LiteLLM proxy (not direct model provider calls).

- **Cloud Run logs show `Failed to export span batch code: 401`**
  - The request reached Langfuse, but OTEL authentication was rejected.
  - Recreate `LANGFUSE_PUBLIC_KEY` and `LANGFUSE_SECRET_KEY` secret versions with `printf '%s' ... | gcloud secrets versions add ...`.
  - Check that the secret values do not contain quotes or trailing newlines.
  - Roll a new Cloud Run revision after updating the secrets so running instances pick up the corrected values.

- **Langfuse OTEL endpoint returns `500` and traces stay empty**
  - Check the Langfuse web container logs for `Failed to upload JSON to S3`.
  - Verify `LANGFUSE_S3_EVENT_UPLOAD_SECRET_ACCESS_KEY` is populated on the Langfuse web and worker containers.
  - If you are using Docker Compose with `${MINIO_ROOT_PASSWORD}`, make sure `/opt/langfuse/.env` exists so Compose can interpolate the variable.

- **Cloud Run revision failed with `Secret ... was not found`**
  - Make sure secret names in `--set-secrets` exactly match Secret Manager names.
  - Make sure you are deploying to the same GCP project where secrets were created.
  - Make sure each secret has at least one enabled version (so `:latest` resolves).

- **Model call returns Vertex AI permission denied**
  - Grant the Cloud Run service account access to Vertex AI, for example `roles/aiplatform.user`.
  - Re-test the LiteLLM `/v1/chat/completions` request after IAM propagation completes.
