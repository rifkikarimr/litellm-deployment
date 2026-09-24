SHELL := /bin/bash

PYTHON ?= python3
LITELLM_VERSION := $(shell cat .litellm-version)

.PHONY: validate test test-fallback compile yaml-check scan-secrets scan-history-secrets compose-config docker-build up down restart ps logs test-openai test-gemini test-live-fallback health

validate: compile yaml-check test scan-secrets scan-history-secrets compose-config

compile:
	$(PYTHON) -m compileall -q scripts tests

yaml-check:
	$(PYTHON) scripts/validate_config.py

test:
	LITELLM_LOCAL_MODEL_COST_MAP=True $(PYTHON) -m unittest discover -s tests -v

test-fallback:
	LITELLM_LOCAL_MODEL_COST_MAP=True $(PYTHON) -m unittest tests.test_fallback -v

scan-secrets:
	$(PYTHON) scripts/scan_secrets.py

scan-history-secrets:
	$(PYTHON) scripts/scan_secrets.py --history

compose-config:
	@test -f .env || cp .env.example .env
	docker compose config --quiet

docker-build:
	docker build --build-arg LITELLM_VERSION=$(LITELLM_VERSION) -t litellm-gateway:$(LITELLM_VERSION) .

up:
	@test -f .env || { echo "Copy .env.example to .env and replace placeholders first."; exit 1; }
	docker compose up -d --build

down:
	docker compose down

restart: down up

ps:
	docker compose ps

logs:
	docker compose logs -f litellm

health:
	$(PYTHON) scripts/smoke_test.py

test-openai:
	LITELLM_MODEL=openai-direct $(PYTHON) scripts/live_test.py

test-gemini:
	LITELLM_MODEL=gemini-direct $(PYTHON) scripts/live_test.py

test-live-fallback:
	$(PYTHON) scripts/live_fallback_test.py
