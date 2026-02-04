FROM python:3.11-slim

# System deps (openssl/node) - prisma engine butuh libssl di OS
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates curl openssl \
    nodejs npm \
  && rm -rf /var/lib/apt/lists/*

# Install LiteLLM Proxy
RUN pip install --no-cache-dir "litellm[proxy]" google-cloud-aiplatform prisma

WORKDIR /app

# Copy config + schema prisma (WAJIB untuk build dari pip)
COPY config.yaml /app/config.yaml
COPY schema.prisma /app/schema.prisma

# Generate prisma client (tanpa butuh connect DB)
ENV PATH="/usr/local/bin:${PATH}"
RUN python -c "import shutil; print('prisma-client-py=', shutil.which('prisma-client-py'))" \
 && python -c "import shutil; print('prisma=', shutil.which('prisma'))" \
 && DATABASE_URL="postgresql://REDACTED prisma generate --schema=/app/schema.prisma


EXPOSE 8080

# Start proxy (port mengikuti Cloud Run)
CMD ["sh", "-lc", "litellm --config /app/config.yaml --host 0.0.0.0 --port ${PORT:-8080} --detailed_debug"]
