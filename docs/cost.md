# Cost

## Cost drivers

- OpenAI input, cached input, output, and tool usage
- Gemini input, output, thinking, and tool usage
- Retry attempts and cross-provider fallback calls
- Cloud Run CPU, memory, instance floor, and request duration
- PostgreSQL compute, storage, backup, and network traffic
- Langfuse Cloud usage or self-hosted compute, database, object storage, and operations
- Centralized logs, traces, retention, and network egress

Exact prices are intentionally not embedded because provider and regional pricing changes. Review current official calculators and pricing pages before deployment.

## Controls

- Use stable client aliases so operators can change the backing model without client releases.
- Set virtual-key budgets, token-per-minute, request-per-minute, and model allowlists.
- Bound request `max_tokens` and reject unexpectedly large inputs at the application layer.
- Keep retries bounded; a retry plus fallback can multiply inference cost.
- Choose a primary/fallback pair based on measured quality and cost, not headline pricing alone.
- Use Cloud Run scale-to-zero for intermittent workloads when cold starts are acceptable.
- Set a conservative maximum instance count aligned with database connection capacity.
- Define log and trace retention, sampling, and payload policies.
- Alert on spend by key/team and on unexpected fallback rates.

Fallback is an availability mechanism, not a cost optimizer. A cheaper fallback can still increase total cost if requests repeatedly hit the primary first.
