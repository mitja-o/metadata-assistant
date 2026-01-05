# OLLAMA utilities
# ================

MODEL=llama3.2

.PHONY: ollama-start
ollama-start ollama:
	ollama start

.PHONY: ollama-run-moodel
ollama-run-model run-model:
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
