SHELL := /bin/bash

LITELLM_VERSION := $(shell cat .litellm-version)
TOOLS_VENV := .venv-prisma-tools
TOOLS_PYTHON := $(TOOLS_VENV)/bin/python
TOOLS_PRISMA := $(TOOLS_VENV)/bin/prisma

.PHONY: tools schema-sync prisma-validate prisma-db-push prisma-generate prisma-reconcile

$(TOOLS_PYTHON):
	python3 -m venv $(TOOLS_VENV)
	$(TOOLS_PYTHON) -m pip install --upgrade pip
	$(TOOLS_PYTHON) -m pip install "litellm[proxy]==$(LITELLM_VERSION)" prisma

tools: $(TOOLS_PYTHON)

schema-sync: $(TOOLS_PYTHON)
	$(TOOLS_PYTHON) -c 'import shutil; from pathlib import Path; import litellm.proxy; src = Path(litellm.proxy.__file__).resolve().parent / "schema.prisma"; dst = Path("schema.prisma").resolve(); shutil.copy2(src, dst); print(f"Synced {src} -> {dst}")'

prisma-validate: $(TOOLS_PYTHON)
	@DB_URL="$${DATABASE_URL:-$$(grep '^DATABASE_URL=' .env 2>/dev/null | cut -d= -f2-)}"; \
	test -n "$$DB_URL" || { echo "DATABASE_URL is required (export it or add it to .env)."; exit 1; }; \
	PATH="$(abspath $(TOOLS_VENV))/bin:$$PATH" DATABASE_URL="$$DB_URL" $(TOOLS_PRISMA) validate --schema=schema.prisma

prisma-db-push: $(TOOLS_PYTHON)
	@DB_URL="$${DATABASE_URL:-$$(grep '^DATABASE_URL=' .env 2>/dev/null | cut -d= -f2-)}"; \
	test -n "$$DB_URL" || { echo "DATABASE_URL is required (export it or add it to .env)."; exit 1; }; \
	PATH="$(abspath $(TOOLS_VENV))/bin:$$PATH" DATABASE_URL="$$DB_URL" $(TOOLS_PRISMA) db push --schema=schema.prisma --skip-generate

prisma-generate: $(TOOLS_PYTHON)
	@DB_URL="$${DATABASE_URL:-$$(grep '^DATABASE_URL=' .env 2>/dev/null | cut -d= -f2-)}"; \
	test -n "$$DB_URL" || { echo "DATABASE_URL is required (export it or add it to .env)."; exit 1; }; \
	PATH="$(abspath $(TOOLS_VENV))/bin:$$PATH" DATABASE_URL="$$DB_URL" $(TOOLS_PRISMA) generate --schema=schema.prisma

prisma-reconcile: schema-sync prisma-validate prisma-db-push prisma-generate
	@echo "Prisma schema reconciled for LiteLLM $(LITELLM_VERSION)."
