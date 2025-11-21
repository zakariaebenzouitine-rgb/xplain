# ============================================================
# Makefile for XPLAIN
#
# Goals:
# - Simple local setup for any coworker
# - Simple local API run
# - Simple Docker local run
# - Ready for Artifact Registry + Cloud Run later
#
# IMPORTANT:
# - No authentication logic here.
# - Coworkers authenticate with gcloud OUTSIDE the repo.
# ============================================================


# ======================#
# Install, clean, test  #
# ======================#

install_requirements:
	# Install runtime requirements only (FastAPI + inference deps)
	@pip install -r requirements.txt

install:
	# Install package in editable mode
	# (needed so "import xplain_package" works)
	@pip install . -U

clean:
	# Remove any cached / build artifacts
	@rm -f */version.txt
	@rm -f .coverage
	@rm -fr */__pycache__ */*.pyc __pycache__
	@rm -fr build dist
	@rm -fr proj-*.dist-info
	@rm -fr proj.egg-info

test_structure:
	# Run the repo structure test script
	@bash tests/test_structure.sh


# ======================#
#          API          #
# ======================#

run_api:
	# Run FastAPI locally with auto-reload on port 8000
	uvicorn api.fast:app --reload --port 8000


# ======================#
#          GCP          #
# ======================#

gcloud-set-project:
	# Set gcloud default project (uses GCP_PROJECT from .env)
	gcloud config set project $(GCP_PROJECT)


# ======================#
#         Docker        #
# ======================#

# ------------------------------------------------------------
# Local images
# - Uses your local machine architecture
# - Great for dev/testing
# ------------------------------------------------------------

docker_build_local:
	# Build a local docker image tagged as api:local
	docker build --tag=$(DOCKER_IMAGE_NAME):local .

docker_run_local:
	# Run local docker image
	#  - maps container 8080 -> local DOCKER_LOCAL_PORT
	#  - loads environment variables from .env
	docker run \
		-e PORT=8000 -p $(DOCKER_LOCAL_PORT):8000 \
		--env-file .env \
		$(DOCKER_IMAGE_NAME):local

docker_run_local_interactively:
	# Run local docker image and open a bash shell inside
	docker run -it \
		-e PORT=8000 -p $(DOCKER_LOCAL_PORT):8000 \
		--env-file .env \
		$(DOCKER_IMAGE_NAME):local \
		bash


# ------------------------------------------------------------
# Cloud images
# - Uses linux/amd64 (compatible with Cloud Run)
# ------------------------------------------------------------

# Build destination used by Artifact Registry / Cloud Run
DOCKER_IMAGE_PATH := $(GCP_REGION)-docker.pkg.dev/$(GCP_PROJECT)/$(DOCKER_REPO_NAME)/$(DOCKER_IMAGE_NAME)

docker_show_image_path:
	# Print final Artifact Registry image path
	@echo $(DOCKER_IMAGE_PATH)

docker_build:
	# Build prod image for cloud (linux/amd64)
	docker build \
		--platform linux/amd64 \
		-t $(DOCKER_IMAGE_PATH):prod .

docker_build_alternative:
	# Alternative build using buildx
	# Useful if docker_build fails on some machines
	docker buildx build --load \
		--platform linux/amd64 \
		-t $(DOCKER_IMAGE_PATH):prod .

docker_run:
	# Run prod image locally (linux/amd64)
	docker run \
		--platform linux/amd64 \
		-e PORT=8000 -p $(DOCKER_LOCAL_PORT):8000 \
		--env-file .env \
		$(DOCKER_IMAGE_PATH):prod

docker_run_interactively:
	# Run prod image locally and open a bash shell
	docker run -it \
		--platform linux/amd64 \
		-e PORT=8000 -p $(DOCKER_LOCAL_PORT):8000 \
		--env-file .env \
		$(DOCKER_IMAGE_PATH):prod \
		bash


# ------------------------------------------------------------
# Push and deploy to cloud (NO AUTH HANDLING HERE)
# ------------------------------------------------------------

docker_allow:
	# Allows docker to push to Artifact Registry
	# Requires user already authenticated with gcloud
	gcloud auth configure-docker $(GCP_REGION)-docker.pkg.dev

docker_create_repo:
	# Create an Artifact Registry docker repo
	# (only needed once per GCP project)
	gcloud artifacts repositories create $(DOCKER_REPO_NAME) \
		--repository-format=docker \
		--location=$(GCP_REGION) \
		--description="Repository for storing docker images"

docker_push:
	# Push prod image to Artifact Registry
	docker push $(DOCKER_IMAGE_PATH):prod

docker_deploy:
	# Deploy to Cloud Run using the prod image
	# Requires .env.yaml (real one, NOT the sample)
	gcloud run deploy \
		--image $(DOCKER_IMAGE_PATH):prod \
		--memory $(GAR_MEMORY) \
		--region $(GCP_REGION) \
		--env-vars-file .env.yaml


# ------------------------------------------------------------
# One-shot prod build + push (Artifact Registry)
# ------------------------------------------------------------

docker_prod:
	# Convenience target:
	# 1) build prod image (cloud compatible)
	# 2) push to Artifact Registry
	#
	# Still requires gcloud auth OUTSIDE repo.
	@echo "Building prod image for Artifact Registry..."
	$(MAKE) docker_build
	@echo "Pushing prod image to Artifact Registry..."
	$(MAKE) docker_push
	@echo "Prod image ready at: $(DOCKER_IMAGE_PATH):prod"
