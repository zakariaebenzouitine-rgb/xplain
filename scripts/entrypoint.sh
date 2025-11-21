#!/usr/bin/env bash
# ============================================================
# entrypoint.sh
#
# Container entrypoint for XPLAIN.
#
# This script runs BEFORE uvicorn starts.
#
# Sequence:
#   1) Optional GCS model download (no-op if GCS_MODEL_URI empty)
#   2) Start FastAPI server
#
# Why?
#   - In Cloud Run, model folder is not inside the image.
#   - So we download it at startup if a GCS URI is provided.
#   - Local dev stays unchanged (no-op).
# ============================================================

# Stop immediately if any command fails
set -e

echo "[entrypoint] Step 1/2: Optional GCS model download..."
python -m xplain_package.io.gcs

echo "[entrypoint] Step 2/2: Starting FastAPI..."
# exec replaces this bash process with uvicorn (clean signal handling)
exec uvicorn api.fast:app --host 0.0.0.0 --port 8080
