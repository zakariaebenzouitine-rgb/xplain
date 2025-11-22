# ============================================================
# Makefile - XPLAIN
# ============================================================

# ------------------------------------------------------------
# Project / Cloud defaults (can be overridden by env/.envrc)
# ------------------------------------------------------------
GCP_PROJECT ?= project-id-123456
GCP_REGION  ?= europe-west1

DOCKER_REPO_NAME  ?= docker
DOCKER_IMAGE_NAME ?= api
DOCKER_LOCAL_PORT ?= 8080

GAR_MEMORY ?= 2Gi

# Default image URI for Artifact Registry
AR_IMAGE_URI := $(GCP_REGION)-docker.pkg.dev/$(GCP_PROJECT)/$(DOCKER_REPO_NAME)/$(DOCKER_IMAGE_NAME)

# ------------------------------------------------------------
# Helpers
# ------------------------------------------------------------
.PHONY: help
help:
	@echo "Available targets:"
	@grep -E '^[a-zA-Z0-9_\-]+:.*?## ' Makefile | \
		sed 's/:.*## / - /'

# ------------------------------------------------------------
# Local dev
# ------------------------------------------------------------
install: ## Install package locally
	pip install -e .

run_api_local: ## Run FastAPI locally with uvicorn (port 8000)
	uvicorn api.fast:app --reload --port 8000

# ------------------------------------------------------------
# Docker local
# ------------------------------------------------------------
docker_build_local: ## Build docker image for local usage
	docker build --tag=$(DOCKER_IMAGE_NAME):local .

docker_run_local:
	# Run local docker image
	# - container listens on 8080 (entrypoint default)
	# - maps container 8080 -> your local DOCKER_LOCAL_PORT
	# - loads env vars from .env
	# - mounts ./models into /app/models (required offline finetuned model)
	# - if host ADC exists, mount it so GCS downloads work in container
	@ADC_FILE="$(HOME)/.config/gcloud/application_default_credentials.json"; \
	MOUNT_ADC=""; ENV_ADC=""; ENV_PROJECT=""; \
	if [ -f "$$ADC_FILE" ]; then \
		echo "[make] Found host ADC -> mounting into container for GCS access"; \
		MOUNT_ADC="-v $$ADC_FILE:/tmp/adc.json:ro"; \
		ENV_ADC="-e GOOGLE_APPLICATION_CREDENTIALS=/tmp/adc.json"; \
	fi; \
	if [ -n "$(GCP_PROJECT)" ]; then \
		ENV_PROJECT="-e GOOGLE_CLOUD_PROJECT=$(GCP_PROJECT)"; \
	fi; \
	docker run --rm \
		-e PORT=8080 \
		-p $(DOCKER_LOCAL_PORT):8080 \
		--env-file .env \
		-v $(PWD)/models:/app/models \
		$$MOUNT_ADC $$ENV_ADC $$ENV_PROJECT \
		$(DOCKER_IMAGE_NAME):local

docker_run_local_interactively:
	# Run local docker image and open a bash shell inside
	# Same mounts/env as docker_run_local
	@ADC_FILE="$(HOME)/.config/gcloud/application_default_credentials.json"; \
	MOUNT_ADC=""; ENV_ADC=""; ENV_PROJECT=""; \
	if [ -f "$$ADC_FILE" ]; then \
		echo "[make] Found host ADC -> mounting into container for GCS access"; \
		MOUNT_ADC="-v $$ADC_FILE:/tmp/adc.json:ro"; \
		ENV_ADC="-e GOOGLE_APPLICATION_CREDENTIALS=/tmp/adc.json"; \
	fi; \
	if [ -n "$(GCP_PROJECT)" ]; then \
		ENV_PROJECT="-e GOOGLE_CLOUD_PROJECT=$(GCP_PROJECT)"; \
	fi; \
	docker run -it --rm \
		-e PORT=8080 \
		-p $(DOCKER_LOCAL_PORT):8080 \
		--env-file .env \
		-v $(PWD)/models:/app/models \
		$$MOUNT_ADC $$ENV_ADC $$ENV_PROJECT \
		$(DOCKER_IMAGE_NAME):local \
		bash

# ------------------------------------------------------------
# Docker prod (Artifact Registry)
# ------------------------------------------------------------
docker_build: ## Build prod image for cloud (linux/amd64)
	docker build \
		--platform linux/amd64 \
		-t $(AR_IMAGE_URI):prod .

docker_push: ## Push prod image to Artifact Registry
	docker push $(AR_IMAGE_URI):prod

docker_prod: ## Build + push prod image
	@echo "Convenience target:"
	@echo "1) build prod image (cloud compatible)"
	@echo "2) push to Artifact Registry"
	@echo "#"
	@echo "Still requires gcloud auth OUTSIDE repo."
	@echo "Building prod image for Artifact Registry..."
	$(MAKE) docker_build
	@echo "Pushing prod image to Artifact Registry..."
	$(MAKE) docker_push

docker_show_image_path: ## Print final Artifact Registry image path
	@echo $(AR_IMAGE_URI)

# ------------------------------------------------------------
# Cloud Run deploy
# ------------------------------------------------------------
deploy_cloud_run: ## Deploy Cloud Run using current prod image + .env.yaml
	gcloud run deploy xplain-api \
		--image $(AR_IMAGE_URI):prod \
		--region $(GCP_REGION) \
		--platform managed \
		--allow-unauthenticated \
		--memory $(GAR_MEMORY) \
		--env-vars-file .env.yaml
