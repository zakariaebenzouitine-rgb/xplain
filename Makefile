# ============================================================
# Makefile for XPLAIN (Inference-only)
#
# We keep the original target names your coworkers expect,
# and add a few safe helpers for inference + dev ergonomics.
#
# IMPORTANT POLICY:
# - No authentication / credentials logic here.
# - Cloud-ready targets are kept as placeholders,
#   but auth-dependent ones are commented out.
#
# Examples:
#   make install_requirements
#   make install-dev
#   make run_api
#   make predict IMG=raw_data/sample.png
#   make docker_build_local
#   make docker_run_local
# ============================================================

# Use bash for better scripting support
SHELL := /bin/bash

# ------------------------------------------------------------
# Defaults (can override like: make run_api PORT=9000)
# ------------------------------------------------------------
PORT ?= 8000
IMG ?= raw_data/sample.png

# Docker settings (also in .env.example)
DOCKER_LOCAL_PORT ?= 8080
DOCKER_REPO_NAME ?= docker
DOCKER_IMAGE_NAME ?= api
DOCKER_TAG ?= local

# Cloud image path (kept from your original)
DOCKER_IMAGE_PATH := $(GCP_REGION)-docker.pkg.dev/$(GCP_PROJECT)/$(DOCKER_REPO_NAME)/$(DOCKER_IMAGE_NAME)

# ------------------------------------------------------------
# Helper: load .env before running commands
# Explanation:
# - set -a exports all loaded variables
# - source .env loads env vars if the file exists
# - set +a stops exporting after that
# ------------------------------------------------------------
define load_env
	set -a; \
	[ -f .env ] && source .env; \
	set +a;
endef


#======================#
# Install, clean, test #
#======================#

install_requirements:
	@echo "Installing runtime dependencies..."
	@pip install -r requirements.txt
	@pip install -e .

# Keep your original "install" name too
install:
	@echo "Installing package (editable)..."
	@pip install -e . -U

# NEW: install dev stack (keeps notebooks tools)
install-dev:
	@echo "Installing dev dependencies..."
	@pip install -r requirements_dev.txt
	@pip install -e .

clean:
	@echo "Cleaning build + cache files..."
	@rm -f */version.txt
	@rm -f .coverage
	@rm -fr */__pycache__ */*.pyc __pycache__
	@rm -fr build dist
	@rm -fr proj-*.dist-info
	@rm -fr proj.egg-info

test_structure:
	@bash tests/test_structure.sh

# NEW: pytest runner (future-proof)
test:
	@echo "Running pytest..."
	@pytest -q

# NEW: formatting & linting targets (safe for coworkers)
format:
	@echo "Formatting with black..."
	@black src api

lint:
	@echo "Linting with ruff..."
	@ruff check src api


#======================#
#          API         #
#======================#

# Keep your original name, but now load .env automatically
run_api:
	@echo "Starting FastAPI on port $(PORT)..."
	@$(load_env) uvicorn api.fast:app --reload --port $(PORT)

# NEW: quick local prediction without the API
# Usage:
#   make predict IMG=raw_data/sample.png
predict:
	@echo "Running local prediction on $(IMG)..."
	@$(load_env) python -c "from xplain_package import predict_caption; print(predict_caption('$(IMG)'))"


#======================#
#          GCP         #
#======================#

# Placeholder only (no auth required)
gcloud-set-project:
	gcloud config set project $(GCP_PROJECT)

# NOTE:
# We intentionally do NOT include any gcloud auth targets here.
# Whoever deploys later will handle auth in their environment.


#======================#
#         Docker       #
#======================#

# Local images - using local computer's architecture
# i.e. linux/amd64 for Windows / Linux / Apple with Intel chip
#      linux/arm64 for Apple with Apple Silicon (M1 / M2 chip)

docker_build_local:
	@echo "Building local Docker image..."
	docker build --tag=$(DOCKER_IMAGE_NAME):local .

docker_run_local:
	@echo "Running local Docker container on port $(DOCKER_LOCAL_PORT)..."
	docker run \
		-e PORT=8000 -p $(DOCKER_LOCAL_PORT):8000 \
		--env-file .env \
		$(DOCKER_IMAGE_NAME):local

docker_run_local_interactively:
	@echo "Running local Docker container interactively..."
	docker run -it \
		-e PORT=8000 -p $(DOCKER_LOCAL_PORT):8000 \
		--env-file .env \
		$(DOCKER_IMAGE_NAME):local \
		bash

# Cloud images - using architecture compatible with cloud, i.e. linux/amd64

docker_show_image_path:
	@echo $(DOCKER_IMAGE_PATH)

docker_build:
	@echo "Building cloud-compatible Docker image (linux/amd64)..."
	docker build \
		--platform linux/amd64 \
		-t $(DOCKER_IMAGE_PATH):prod .

# Alternative if previous doesn´t work. Needs additional setup.
docker_build_alternative:
	@echo "Building cloud image with buildx (linux/amd64)..."
	docker buildx build --load \
		--platform linux/amd64 \
		-t $(DOCKER_IMAGE_PATH):prod .

docker_run:
	@echo "Running cloud-compatible Docker image locally..."
	docker run \
		--platform linux/amd64 \
		-e PORT=8000 -p $(DOCKER_LOCAL_PORT):8000 \
		--env-file .env \
		$(DOCKER_IMAGE_PATH):prod

docker_run_interactively:
	@echo "Running cloud-compatible Docker image interactively..."
	docker run -it \
		--platform linux/amd64 \
		-e PORT=8000 -p $(DOCKER_LOCAL_PORT):8000 \
		--env-file .env \
		$(DOCKER_IMAGE_PATH):prod \
		bash


# ----------------------------
# Push and deploy to cloud (placeholders only)
# ----------------------------

# AUTH TARGET REMOVED ON PURPOSE:
# We avoid authentication/credentials in this repo.
# Whoever deploys later will run their own auth steps.
#
# docker_allow:
# 	gcloud auth configure-docker $(GCP_REGION)-docker.pkg.dev

docker_create_repo:
	@echo "Creating Artifact Registry repo (no auth handled here)..."
	gcloud artifacts repositories create $(DOCKER_REPO_NAME) \
		--repository-format=docker \
		--location=$(GCP_REGION) \
		--description="Repository for storing docker images"

docker_push:
	@echo "Pushing Docker image to Artifact Registry..."
	docker push $(DOCKER_IMAGE_PATH):prod

docker_deploy:
	@echo "Deploying to Cloud Run (assumes deployer is already authenticated)..."
	gcloud run deploy \
		--image $(DOCKER_IMAGE_PATH):prod \
		--memory $(GAR_MEMORY) \
		--region $(GCP_REGION) \
		--env-vars-file .env.yaml
