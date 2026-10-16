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

# Evaluations
# ===========

# Data Preparation
# ----------------

DATA_DIR=_data
GBIF_DATA_DIR=${DATA_DIR}/gbif_data_archive

# unpack the download
${GBIF_DATA_DIR}/.key: ${DATA_DIR}/gbif_data_archive.zip
	rm -rf ${GBIF_DATA_DIR}/.key
	unzip ${DATA_DIR}/gbif_data_archive.zip -d ${DATA_DIR}
	@echo "🗝️ Making a target key"
	touch ${GBIF_DATA_DIR}/.key

# Create the output storage directory
${GBIF_DATA_DIR}/out/.key: ${GBIF_DATA_DIR}/.key
	rm -rf ${GBIF_DATA_DIR}/out/.key
	mkdir -p ${GBIF_DATA_DIR}/out
	@echo "🗝️ Making a target key"
	touch ${GBIF_DATA_DIR}/out/.key

${DATA_DIR}/.key: ${GBIF_DATA_DIR}/out/.key
	rm -rf ${DATA_DIR}/.key
	@echo "🗝️ Making a target key"
	touch ${DATA_DIR}/.key

# Experiment Runs
# ---------------

# prepare the case inputs
evaluation/runtime/gbif_cases.csv: ${DATA_DIR}/.key ${GBIF_DATA_DIR}/downloaded_gbif_cases.csv
	mkdir -p evaluation/runtime/
	cp ${GBIF_DATA_DIR}/downloaded_gbif_cases.csv evaluation/runtime/gbif_cases.csv

# use the default experiment scenarios unless already defined
evaluation/runtime/experiment_scenarios.csv: evaluation/defaults/experiment_scenarios.csv
	mkdir -p evaluation/runtime/
	cp evaluation/defaults/experiment_scenarios.csv evaluation/runtime/experiment_scenarios.csv

# run the experiments
.PHONY: evaluate
evaluate: pyproject.toml evaluation evaluation/runtime/gbif_cases.csv evaluation/runtime/experiment_scenarios.csv
	@echo "⚗️ Running the experiments"
	mkdir -p evaluation/reports/runs/
	uv run --group dev --group sandbox --group observability pytest evaluation \
		| tee 'evaluation/reports/runs/run-$(shell date +%s).txt'

# Experiment Analyses
# -------------------

# copy the experiment outputs for analysis
analysis/experiment_cross_scenarios_cases.log.csv: evaluation/runtime/experiment_cross_scenarios_cases.log.csv
	cp evaluation/runtime/experiment_cross_scenarios_cases.log.csv analysis/experiment_cross_scenarios_cases.log.csv

prep-analysis: analysis/experiment_cross_scenarios_cases.log.csv
	@echo "⚗️ Experiment results are ready for analysis"
	ls -l analysis/experiment_cross_scenarios_cases.log.csv

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
	cd utils/lmnr && docker compose up --pull never

.PHONY: check-lmnr-frontend-port
check-lmnr-frontend-port: ./utils/lmnr
	docker container inspect -f '{{.NetworkSettings.Ports}}' lmnr-frontend-1

# Local dev platform
# ==================

.PHONY: start-local-notebook
start-local-notebook start-lnb:
	pip install -v . --group notebook
	jupyter lab

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
