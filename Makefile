# Dev utilities
# =============
.PHONY: cleanup
cleanup: pyproject.toml
	uv run isort massi
	uv run black massi

.PHONY: check
check: pyproject.toml
	uv run mypy massi

.PHONY: test
test: pyproject.toml
	uv run pytest

# OLLAMA utilities
# ================

MODEL=llama3.2

.PHONY: ollama-start
start-ollama ollama:
	ollama start

.PHONY: ollama-run-moodel
run-ollama-model run-model:
	ollama run ${MODEL}

# Containerized (dev) runtime
# ===========================

NB_CONTAINER_NAME = miagis-assistant-jupyter-nb

.PHONY: start-notebook
start-notebook start-nb:
	docker compose --profile nb-only up

.PHONY: stop
stop: docker-compose.yaml
	docker compose down

.PHONY: list-jupyter
list-jupyter:
	docker exec $(NB_CONTAINER_NAME) jupyter server list

.PHONY: attach-jupyter-container
attach-jupyter-container:
	docker exec -it $(NB_CONTAINER_NAME) bash
