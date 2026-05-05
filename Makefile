# Dev utilities
# =============
.PHONY: format
format: pyproject.toml
	uv run isort massi
	uv run black massi --target-version=py313

.PHONY: clean-build-artifacts
clean-build-artifacts clean-build: pyproject.toml
	rm -rf build
	rm -rf massi.egg-info
	rm -rf dist

.PHONY: clean-cache
clean-cache: pyproject.toml clean-build-artifacts
	find . -type d -name "__pycache__" -exec rm -r {} +
	find . -type f -name "*.pyc" -exec rm -f {} +
	find . -type f -name "*.pyo" -exec rm -f {} +

.PHONY: check
check: pyproject.toml
	uv run mypy massi

.PHONY: test
test: pyproject.toml
	uv run pytest

.PHONY: evaluate
evaluate: pyproject.toml _evaluation
	mkdir -p _evaluation/reports/runs/
	uv run --group dev --group experiments --group sandbox pytest _evaluation \
		| tee '_evaluation/reports/runs/run-$(shell date +%s).txt'

# Developer hints
# ===============

.PHONY: dev-hint
dev-hint:
	@echo "===== OLLAMA ====="
	@echo "To get Ollama up:       $$ make start-ollama"
	@echo "To get local models up: $$ make run-model"
	@echo "\n===== Observability ====="
	@echo "To get Luminar tracer running: $$ make start-lmnr"
	@echo "\n===== Notebook ======"
	@echo "To get the Notebook running: $$ make start-nb"

# OLLAMA utilities
# ================

MODEL=lfm2.5-thinking

.PHONY: ollama-start
start-ollama ollama:
	ollama start

.PHONY: ollama-run-moodel
run-ollama-model run-model:
	ollama run ${MODEL}

# Observability tooling
# =====================

.PHONY: start-observer-lmnr
start-observer-lmnr start-luminar start-lmnr: ./utils/lmnr
	cd utils/lmnr && docker compose up

.PHONY: check-lmnr-frontend-port
check-lmnr-frontend-port: ./utils/lmnr
	docker container inspect -f '{{.NetworkSettings.Ports}}' lmnr-frontend-1

# Containerized (dev) runtime
# ===========================

NB_CONTAINER_NAME = miagis-assistant-jupyter-nb

.PHONY: start-notebook
start-notebook start-nb:
	docker compose --profile nb-only up

.PHONY: stop
stop: docker-compose.yaml
	docker compose down

.PHONY: list-jupyterd
list-jupyter:
	docker exec $(NB_CONTAINER_NAME) jupyter server list

.PHONY: attach-jupyter-container
attach-jupyter-container:
	docker exec -it $(NB_CONTAINER_NAME) bash
