# LiteLLM on Cloud Run (R&D) + PostgreSQL on GCE (Docker)

This repo documents an R&D setup where **LiteLLM Proxy + Web UI** runs on **Google Cloud Run** (public), while **PostgreSQL** runs on a **GCE VM** via Docker. Cloud Run reaches the database over **private networking** using **Direct VPC egress**.

## Architecture

- **Cloud Run (public ingress):** LiteLLM Proxy + UI
- **GCE VM (private IP):** PostgreSQL (Docker Compose)
- **Networking:** Cloud Run → VPC/Subnet → VM private IP (Direct VPC egress) :contentReference[oaicite:0]{index=0}
- **Secrets:** Secret Manager → Cloud Run environment variables :contentReference[oaicite:1]{index=1}

## Key concepts

- Cloud Run containers must **listen on the port provided in the `PORT` env var** and usually on `0.0.0.0` (not `127.0.0.1`). :contentReference[oaicite:2]{index=2}
- LiteLLM default port is **4000**, but you can override with `--port` and `--host`. :contentReference[oaicite:3]{index=3}
- Direct VPC egress lets Cloud Run services/jobs reach private resources in a VPC **without** a VPC connector. :contentReference[oaicite:4]{index=4}

## Repository contents (example)

- `Dockerfile` – LiteLLM container image
- `config.yaml` – LiteLLM proxy config (models + DB settings)
- `postgres/` – VM Postgres docker-compose + `pg_hba.conf`

> Do **not** commit secrets (`.env`, DB passwords, master keys). Use Secret Manager.

## Deployment summary (high level)

### 1) PostgreSQL (GCE VM, Docker Compose)
- Run Postgres on a VM private IP.
- Ensure Postgres listens externally and host-based auth allows Cloud Run subnet (via `pg_hba.conf`).
- Avoid mounting `pg_hba.conf` inside `PGDATA` as read-only (can cause permission/chown startup issues).

### 2) Secrets (Secret Manager)
Create secrets such as:
- `DATABASE_URL_LLM`
- `LITELLM_MASTER_KEY`
- `LITELLM_SALT_KEY`
- `UI_USERNAME`, `UI_PASSWORD`

Then mount them into Cloud Run as env vars. :contentReference[oaicite:5]{index=5}

### 3) LiteLLM (Cloud Run)
Run LiteLLM so it binds to Cloud Run’s port:
- `--host 0.0.0.0`
- `--port ${PORT:-8080}`

LiteLLM supports these CLI flags. :contentReference[oaicite:6]{index=6}

## Validation checks

1. **UI reachable** (Cloud Run URL)
2. **DB persistence works** (create a Virtual Key → refresh → still exists after redeploy)
3. **Inference works** via OpenAI-compatible endpoint (e.g., `/v1/chat/completions`)
4. **Policy enforcement works** (e.g., key restricted to certain models returns “key_model_access_denied”)

## Troubleshooting notes (what we hit)

- **Cloud Run “failed to start and listen on PORT=8080”**  
  Root cause: app didn’t bind to `PORT` or didn’t listen on `0.0.0.0`. :contentReference[oaicite:7]{index=7}

- **DB connectivity testing as a Service failed**  
  A Cloud Run *service* must listen on `PORT`. For one-off connectivity tests, use a *Job* (jobs do not require listening on a port). :contentReference[oaicite:8]{index=8}

- **Postgres data directory version mismatch**  
  If the data volume was initialized by a different major Postgres version, the container will fail. (Fix by matching major version or resetting volume for R&D.)

## References
- LiteLLM Proxy CLI (host/port): :contentReference[oaicite:9]{index=9}  
- Cloud Run container contract (PORT): :contentReference[oaicite:10]{index=10}  
- Direct VPC egress: :contentReference[oaicite:11]{index=11}  
- Cloud Run secrets: :contentReference[oaicite:12]{index=12}
