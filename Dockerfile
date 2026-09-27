ARG LITELLM_VERSION=1.100.1
FROM ghcr.io/berriai/litellm-database:${LITELLM_VERSION}

WORKDIR /app
COPY config.yaml /app/config.yaml

ENV PORT=4000
EXPOSE 4000

# Shell expansion keeps the image portable across Docker hosts that set PORT.
ENTRYPOINT ["sh", "-c"]
CMD ["exec litellm --config /app/config.yaml --host 0.0.0.0 --port ${PORT:-4000} --use_v2_migration_resolver"]
