# Operations

## Local lifecycle

```bash
cp .env.example .env
docker compose up -d --build
python3 scripts/smoke_test.py
docker compose logs -f litellm
docker compose down
```

`docker compose down` retains the named PostgreSQL volume. Use an explicit, reviewed volume-removal command only when data loss is intended.

## Health and readiness

The local smoke test calls `/health/liveliness` without invoking a model. Before shifting traffic in a deployed environment, also verify:

1. the new revision is ready and serving traffic;
2. `/health/liveliness` succeeds;
3. authenticated model listing works;
4. one OpenAI direct request succeeds;
5. one Gemini direct request succeeds;
6. a controlled fallback succeeds;
7. a streaming request terminates correctly;
8. usage persists after a container restart;
9. logs and optional traces identify the selected provider.

## Opt-in live provider checks

Live checks are never part of `make validate`. After loading real credentials into
the local environment and starting the gateway, run each paid check explicitly:

```bash
RUN_PAID_PROVIDER_TESTS=1 make test-openai
RUN_PAID_PROVIDER_TESTS=1 make test-gemini
RUN_PAID_PROVIDER_TESTS=1 LITELLM_MODEL=general-chat python3 scripts/live_test.py
RUN_PAID_PROVIDER_TESTS=1 make test-live-fallback
```

`test-live-fallback` does not call OpenAI. It injects a local HTTP 500 response for
the OpenAI primary and makes one real Gemini request through LiteLLM's Router. It
verifies that the primary was attempted before the fallback completed. This is a
controlled Router-level proof; the normal `general-chat` check remains the
end-to-end proxy-path proof.

The explicit `RUN_PAID_PROVIDER_TESTS=1` acknowledgement is required even when
credentials are already present in the environment.

## Cloud Run deployment pattern

Build and publish the image using your chosen CI/CD system, then deploy it with:

- container port supplied through `PORT`;
- minimum and maximum instances chosen from traffic and database connection limits;
- a service account with Secret Manager access;
- secret mappings for provider keys, LiteLLM keys, and `DATABASE_URL`;
- ordinary variables for `PRIMARY_MODEL` and `FALLBACK_MODEL`;
- a network path to managed PostgreSQL;
- stdout/stderr log collection.

The container has no local persistence dependency. Cloud Run local disk is ephemeral; all durable gateway state belongs in PostgreSQL.

## Database changes and upgrades

The image uses LiteLLM's database-enabled distribution so the proxy package and database tooling come from the same pinned release. Before upgrading:

1. read release notes between the old and new versions;
2. back up PostgreSQL and test restore;
3. run the new image against a staging database;
4. validate schema changes and key/model data;
5. run offline, health, direct-provider, fallback, and streaming tests;
6. deploy a new revision with a rollback path.

Do not treat a started build as a successful deployment. Confirm the ready revision, traffic assignment, health, and live API behavior.

## Incident cues

- Increased 429s: inspect provider quotas, virtual-key limits, retry amplification, and cooldown state.
- Timeouts: compare provider latency with the 30-second router timeout.
- No deployments available: inspect cooldown events and recent upstream failures.
- Database errors: stop administrative writes, inspect connectivity and pool saturation, and preserve evidence.
- Missing traces: verify endpoint reachability and keys without printing secret values.
