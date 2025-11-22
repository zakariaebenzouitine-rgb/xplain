#!/usr/bin/env bash
# ============================================================
# scripts/bootstrap_artifact_registry.sh
#
# Purpose:
#   One-time setup for Artifact Registry in a given GCP project.
#
# What it does:
#   1) Loads .env if present (local convenience)
#   2) Enables needed services
#   3) Creates the docker repo if it doesn't exist
#   4) Configures docker auth for Artifact Registry
#
# Design rules (your requirements):
#   - NO authentication here.
#   - NO credentials here.
#   - Deployer must already be logged in with gcloud.
#
# Who runs this?
#   The deployer, in THEIR GCP account, once.
# ============================================================

set -e  # stop on first error

echo "=============================================="
echo "XPLAIN Artifact Registry Bootstrap"
echo "=============================================="

# ------------------------------------------------------------
# 1) Load .env if it exists (local convenience)
# ------------------------------------------------------------
if [ -f ".env" ]; then
  echo "[bootstrap] Loading .env ..."
  set -a
  source .env
  set +a
fi

# ------------------------------------------------------------
# 2) Sanity checks
# ------------------------------------------------------------
: "${GCP_PROJECT:?Missing GCP_PROJECT}"
: "${GCP_REGION:?Missing GCP_REGION}"
: "${DOCKER_REPO_NAME:?Missing DOCKER_REPO_NAME}"

echo "[bootstrap] Project : ${GCP_PROJECT}"
echo "[bootstrap] Region  : ${GCP_REGION}"
echo "[bootstrap] Repo    : ${DOCKER_REPO_NAME}"

# ------------------------------------------------------------
# 3) Set project (safe, no auth)
# ------------------------------------------------------------
echo ""
echo "[bootstrap] Setting gcloud project..."
gcloud config set project "${GCP_PROJECT}"

# ------------------------------------------------------------
# 4) Enable required services
# ------------------------------------------------------------
echo ""
echo "[bootstrap] Enabling required GCP services..."
gcloud services enable artifactregistry.googleapis.com
gcloud services enable run.googleapis.com

# ------------------------------------------------------------
# 5) Create Artifact Registry repo if missing
# ------------------------------------------------------------
echo ""
echo "[bootstrap] Checking if repo exists..."

if gcloud artifacts repositories describe "${DOCKER_REPO_NAME}" \
  --location="${GCP_REGION}" >/dev/null 2>&1; then

  echo "[bootstrap] Repo '${DOCKER_REPO_NAME}' already exists in ${GCP_REGION}."

else
  echo "[bootstrap] Creating repo '${DOCKER_REPO_NAME}'..."
  gcloud artifacts repositories create "${DOCKER_REPO_NAME}" \
    --repository-format=docker \
    --location="${GCP_REGION}" \
    --description="Repository for storing XPLAIN docker images"
fi

# ------------------------------------------------------------
# 6) Configure docker auth for Artifact Registry
# ------------------------------------------------------------
echo ""
echo "[bootstrap] Configuring docker auth for Artifact Registry..."
gcloud auth configure-docker "${GCP_REGION}-docker.pkg.dev"

echo ""
echo "[bootstrap] Done."
echo "Artifact Registry is ready for pushes to:"
echo "  ${GCP_REGION}-docker.pkg.dev/${GCP_PROJECT}/${DOCKER_REPO_NAME}"
