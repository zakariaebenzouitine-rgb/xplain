#!/usr/bin/env bash
# ============================================================
# scripts/deploy_cloud_run.sh
#
# Purpose:
#   Deploy the XPLAIN Docker image to Cloud Run.
#
# Design rules (your requirements):
#   - NO authentication here.
#   - NO credentials here.
#   - Uses env vars from .env or shell.
#   - Uses .env.yaml for Cloud Run env injection.
#
# Who runs this?
#   The deployer, in THEIR GCP account, after:
#     1) gcloud auth login
#     2) gcloud config set project <their-project>
#     3) make docker_prod
# ============================================================

set -e  # stop if any command fails

echo "=============================================="
echo "XPLAIN Cloud Run Deploy Script"
echo "=============================================="

# ------------------------------------------------------------
# 1) Load .env if it exists (local convenience)
# ------------------------------------------------------------
if [ -f ".env" ]; then
  echo "[deploy] Loading .env ..."
  # export all vars defined in .env into current shell
  set -a
  source .env
  set +a
fi

# ------------------------------------------------------------
# 2) Sanity checks for required variables
# ------------------------------------------------------------
: "${GCP_PROJECT:?Missing GCP_PROJECT}"
: "${GCP_REGION:?Missing GCP_REGION}"
: "${DOCKER_REPO_NAME:?Missing DOCKER_REPO_NAME}"
: "${DOCKER_IMAGE_NAME:?Missing DOCKER_IMAGE_NAME}"

# Cloud Run service name
# If you want another name, export CR_SERVICE_NAME before running
CR_SERVICE_NAME="${CR_SERVICE_NAME:-xplain-api}"

# Artifact Registry image path (must match Makefile)
DOCKER_IMAGE_PATH="${GCP_REGION}-docker.pkg.dev/${GCP_PROJECT}/${DOCKER_REPO_NAME}/${DOCKER_IMAGE_NAME}:prod"

echo "[deploy] Project  : ${GCP_PROJECT}"
echo "[deploy] Region   : ${GCP_REGION}"
echo "[deploy] Service  : ${CR_SERVICE_NAME}"
echo "[deploy] Image    : ${DOCKER_IMAGE_PATH}"

# ------------------------------------------------------------
# 3) Ensure .env.yaml exists
# ------------------------------------------------------------
if [ ! -f ".env.yaml" ]; then
  echo ""
  echo "[deploy] ERROR: .env.yaml not found."
  echo "Copy .env.yaml.sample -> .env.yaml and fill values."
  echo ""
  exit 1
fi

# ------------------------------------------------------------
# 4) Deploy to Cloud Run
# ------------------------------------------------------------
echo ""
echo "[deploy] Deploying to Cloud Run..."
echo "NOTE: This assumes you already authenticated with gcloud."
echo ""

gcloud run deploy "${CR_SERVICE_NAME}" \
  --image "${DOCKER_IMAGE_PATH}" \
  --region "${GCP_REGION}" \
  --platform managed \
  --allow-unauthenticated \
  --env-vars-file .env.yaml

echo ""
echo "[deploy] Done."
echo "Cloud Run service deployed with image:"
echo "  ${DOCKER_IMAGE_PATH}"
