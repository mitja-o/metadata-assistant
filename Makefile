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

DATA_DIR=_data
GBIF_DATA_DIR=${DATA_DIR}/gbif_data_archive

# unpack the download
${GBIF_DATA_DIR}/.key: _downloads/gbif_data_archive.zip
	mkdir -p ${DATA_DIR}
	unzip _downloads/gbif_data_archive.zip -d ${DATA_DIR}
	@echo "🗝️ Making a target key"
	touch ${GBIF_DATA_DIR}/.key

# prepare the working data
${GBIF_DATA_DIR}/working_copy/.key: ${GBIF_DATA_DIR}/.key
	@echo "🚚 Preparing the working data"
	mkdir -p ${GBIF_DATA_DIR}/working_copy
	cp -r ${GBIF_DATA_DIR}/data ${GBIF_DATA_DIR}/working_copy
	@echo "🗃️ Unpacking the working data"
	for z in ${GBIF_DATA_DIR}/working_copy/data/*.zip; do \
		echo "~~ placing: $$z --> $${z%.*} ..." ; \
		format=$$(7zz l "$$z" | grep "Type =" | awk '{print $$3}') ; \
		case "$${format}" in \
			"gzip") \
				echo "   (Detected wrapper: $${format})" ; \
				7zz x "$$z" -so > "$$z.tmp" ; \
				7zz x "$$z.tmp" -y -o"$${z%.*}" -xr!".*" -xr!"__*" -xr!"*.xml" > /dev/null ; \
				rm "$$z.tmp" ;; \
			*) \
				echo "   (Detected standard: $${format})" ; \
				7zz x "$$z" -y -o"$${z%.*}" -xr!".*" -xr!"__*" -xr!"*.xml" > /dev/null ;; \
		esac ; \
	done
	@echo "🗝️ Making a target key"
	touch ${GBIF_DATA_DIR}/working_copy/.key

# prepare the ground truth
${GBIF_DATA_DIR}/ground_truth/.key: ${GBIF_DATA_DIR}/working_copy/.key
	@echo "🚚 Preparing the ground truth data"
	mkdir -p ${GBIF_DATA_DIR}/ground_truth/data
	mkdir -p ${GBIF_DATA_DIR}/ground_truth/papers
	mv ${GBIF_DATA_DIR}/data ${GBIF_DATA_DIR}/ground_truth
	mv ${GBIF_DATA_DIR}/papers ${GBIF_DATA_DIR}/ground_truth
	@echo "🗃️ Unpacking the ground truth metadata"
	@for z in ${GBIF_DATA_DIR}/ground_truth/data/*.zip; do \
		echo "~~ placing: $$z --> $${z%.*} ..." ; \
		format=$$(7zz l "$$z" | grep "Type =" | awk '{print $$3}') ; \
		case "$${format}" in \
			"gzip") \
				echo "   (Detected wrapper: $${format})" ; \
				7zz x "$$z" -so > "$$z.tmp" ; \
				7zz x "$$z.tmp" -y -o"$${z%.*}" eml.xml meta.xml > /dev/null ; \
				rm "$$z.tmp" ;; \
			*) \
				echo "   (Detected standard: $${format})" ; \
				7zz x "$$z" -y -o"$${z%.*}" eml.xml meta.xml > /dev/null ;; \
		esac ; \
	done
	@echo "🗝️ Making a target key"
	touch ${GBIF_DATA_DIR}/ground_truth/.key

# Create the output storage directory
${GBIF_DATA_DIR}/out/.key: ${GBIF_DATA_DIR}/ground_truth/.key
	mkdir -p ${GBIF_DATA_DIR}/out
	@echo "🗝️ Making a target key"
	touch ${GBIF_DATA_DIR}/out/.key

${DATA_DIR}/.key: ${GBIF_DATA_DIR}/out/.key
	@echo "🗝️ Making a target key"
	touch ${GBIF_DATA_DIR}/.key

# prepare the case inputs
_evaluation/runtime/gbif_cases.csv: ${DATA_DIR}/.key
	mkdir -p _evaluation/runtime/
	cp ${GBIF_DATA_DIR}/downloaded_gbif_cases.csv _evaluation/runtime/gbif_cases.csv

# run the experiments
.PHONY: evaluate
evaluate: pyproject.toml _evaluation _evaluation/runtime/gbif_cases.csv
	mkdir -p _evaluation/reports/runs/
	uv run --group dev --group sandbox --group observability pytest _evaluation \
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

# Local dev platform
# ==================

.PHONY: start-local-notebook
start-local-notebook start-lnb:
	uv run --group notebook --group dev jupyter lab

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
