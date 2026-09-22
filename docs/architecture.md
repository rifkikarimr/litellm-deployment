# Architecture

## Local reference architecture

```mermaid
flowchart TB
    Client[Client application] -->|OpenAI-compatible HTTP| LiteLLM[LiteLLM Proxy]
    LiteLLM -->|general-chat primary| OpenAI[OpenAI API]
    LiteLLM -. eligible provider failure .-> Gemini[Google Gemini API]
    LiteLLM -->|keys, budgets, usage| PostgreSQL[(PostgreSQL)]
    LiteLLM -. traces when configured .-> Langfuse[Langfuse / OTEL endpoint]

    subgraph Compose[Docker Compose network]
      LiteLLM
      PostgreSQL
    end
```

Only LiteLLM is published, and only on host loopback by default. PostgreSQL has no host port mapping. Provider credentials enter the gateway as runtime environment variables.

## Cloud Run pattern

```mermaid
flowchart LR
    Client --> HTTPS[Cloud Run HTTPS endpoint]
    HTTPS --> LiteLLM[LiteLLM container]
    SecretManager[Google Secret Manager] -->|runtime environment secrets| LiteLLM
    LiteLLM --> OpenAI[OpenAI API]
    LiteLLM -. fallback .-> Gemini[Gemini API]
    LiteLLM --> PostgreSQL[(Managed PostgreSQL)]
    LiteLLM -. optional OTLP .-> Langfuse[Langfuse endpoint]
```

Cloud Run provides ingress and autoscaling, but availability still depends on provider quotas, the database, network paths, regional service health, and configuration correctness. This repository does not provision those resources.

## Component responsibilities

| Component | Responsibility |
| --- | --- |
| Client | Sends OpenAI-compatible requests using `general-chat` |
| LiteLLM | Authenticates, routes, retries, falls back, meters, and logs |
| OpenAI | Primary inference provider |
| Gemini API | Cross-provider fallback and direct validation route |
| PostgreSQL | Virtual keys, teams, budgets, configuration, and usage persistence |
| Langfuse | Optional trace and generation analysis through OTLP |

The model aliases are a contract. Provider model identifiers remain environment-controlled so they can change without forcing client changes.
