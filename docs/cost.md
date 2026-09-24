# Cost

## Cost drivers

- OpenAI input, cached input, output, and tool usage
- Gemini input, output, thinking, and tool usage
- retry attempts and cross-provider fallback calls
- CPU, memory, disk, electricity, or rental cost for the Docker host
- PostgreSQL storage, backup retention, and transfer during restore or migration
- Langfuse Cloud usage or self-hosted compute and storage
- centralized logs, traces, retention, and network egress

Exact prices are intentionally not embedded because provider, hardware, electricity, and hosting prices change.

## Controls

- Use stable client aliases so operators can change the backing model without client releases.
- Set virtual-key budgets, token-per-minute, request-per-minute, and model allowlists.
- Bound request `max_tokens` and reject unexpectedly large inputs at the application layer.
- Keep retries bounded; a retry plus fallback can multiply inference cost.
- Choose primary and fallback models from measured quality and cost.
- Stop the local stack when it is not needed, while preserving the database volume.
- Size the Docker host from measured CPU, memory, disk, and request concurrency.
- Define database backup, log, and trace retention policies.
- Alert on spend by key/team and on unexpected fallback rates.

Fallback is an availability mechanism, not a cost optimizer. A cheaper fallback can still increase total cost when requests first consume primary-provider retries.
