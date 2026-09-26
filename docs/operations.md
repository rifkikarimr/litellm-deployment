# Operations

## Requirements

- Docker Engine with Docker Compose v2
- outbound HTTPS access to the configured model providers
- local disk space for the PostgreSQL named volume
- Python only for repository validation and helper scripts

No GCP account, cloud CLI, managed database, or service account is required.

## First start

```bash
cp .env.example .env
```

Replace every `replace-me` value, then start the complete stack:

```bash
make up
make ps
make health
```

Follow logs with:

```bash
make logs
```

`make down` removes containers and the Compose network but preserves the `postgres-data` volume. Do not remove that volume unless permanent database deletion is intended and a verified backup exists.

## Changing the PostgreSQL password

`POSTGRES_PASSWORD` initializes the database role only when PostgreSQL creates an empty data directory. Editing `.env` later does not change the password stored inside an existing `postgres-data` volume. If `POSTGRES_PASSWORD` and the password inside `DATABASE_URL` are intentionally rotated, synchronize the existing role with:

```bash
make db-sync-password PYTHON=.venv/bin/python
make health PYTHON=.venv/bin/python
```

The synchronization command validates the `.env` relationship, stops LiteLLM, creates a permission-restricted PostgreSQL backup in the operating system's temporary directory, updates only the Compose database role password, and starts LiteLLM again. It does not delete or recreate the volume. A Prisma `P1000` error after changing `.env` is an authentication mismatch, not a schema migration failure.

## Run on another Docker host

1. Clone the repository on the target host.
2. Copy `.env.example` to an untracked `.env` and insert runtime secrets.
3. Keep `LITELLM_BIND_ADDRESS=127.0.0.1` when clients run on the same host.
4. For remote clients, deploy a TLS reverse proxy and firewall policy first, then explicitly set the required bind address.
5. Run `make validate`, `make docker-build`, and `make up`.
6. Confirm `make health`, container health, and PostgreSQL persistence after a restart.

The Compose project owns both LiteLLM and PostgreSQL, so migration to another machine consists of the repository, runtime secrets, and a tested PostgreSQL backup/restore—not provider-specific infrastructure.

## Health and readiness

The smoke test calls `/health/liveliness` without invoking a model. Before accepting traffic, verify:

1. both Compose services are healthy;
2. `/health/liveliness` succeeds;
3. authenticated model listing works;
4. PostgreSQL-backed data persists after `make restart`;
5. logs contain no credentials or unexpected debug payloads.

Provider tests are a separate, explicitly paid validation phase.

## Opt-in live provider checks

Live checks never run as part of `make validate`. After loading real credentials and starting the gateway, each paid check requires explicit acknowledgement:

```bash
RUN_PAID_PROVIDER_TESTS=1 make test-openai
RUN_PAID_PROVIDER_TESTS=1 make test-gemini
RUN_PAID_PROVIDER_TESTS=1 LITELLM_MODEL=general-chat python3 scripts/live_test.py
RUN_PAID_PROVIDER_TESTS=1 make test-live-fallback
```

`test-live-fallback` injects a local HTTP 500 for the primary and makes one real Gemini request. It proves Router fallback behavior but not the full proxy path.

## Database backup and upgrades

PostgreSQL data lives in the `postgres-data` volume. Establish an application-consistent `pg_dump` backup and perform a restore test before upgrades or host migration. Do not treat copying a live volume directory as a verified database backup.

Before upgrading LiteLLM or PostgreSQL:

1. read the relevant release notes;
2. create and verify a PostgreSQL backup;
3. test the new images with restored non-production data;
4. run offline validation and health checks;
5. run explicitly approved provider, fallback, and streaming tests;
6. retain the previous image tag and database backup for rollback.

## Incident cues

- Increased 429s: inspect provider quotas, virtual-key limits, retry amplification, and cooldown state.
- Timeouts: compare provider latency with the 30-second router timeout.
- No deployments available: inspect cooldown events and recent upstream failures.
- Database errors: stop administrative writes, inspect container health and disk capacity, and preserve evidence.
- Missing traces: verify endpoint reachability and keys without printing secret values.
- Host outage: restore the database backup and stack on another Docker-capable host.
