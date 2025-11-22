#!/usr/bin/env bash
set -euo pipefail

echo "[entrypoint] =============================================="
echo "[entrypoint] XPLAIN container starting..."
echo "[entrypoint] =============================================="

MODEL_FAMILY="${MODEL_FAMILY:-blip}"
LOCAL_MODEL_DIR="${LOCAL_MODEL_DIR:-models/cxiu_blip_baseline}"
GCS_MODEL_URI="${GCS_MODEL_URI:-}"
ALLOW_HF_FALLBACK="${ALLOW_HF_FALLBACK:-false}"
PORT="${PORT:-8080}"

echo "[entrypoint] MODEL_FAMILY        = ${MODEL_FAMILY}"
echo "[entrypoint] LOCAL_MODEL_DIR    = ${LOCAL_MODEL_DIR}"
echo "[entrypoint] GCS_MODEL_URI      = ${GCS_MODEL_URI:-<empty>}"
echo "[entrypoint] ALLOW_HF_FALLBACK  = ${ALLOW_HF_FALLBACK}"
echo "[entrypoint] PORT               = ${PORT}"

# If ADC was mounted but GOOGLE_APPLICATION_CREDENTIALS not set, set it.
if [[ -z "${GOOGLE_APPLICATION_CREDENTIALS:-}" ]]; then
  if [[ -f "/tmp/adc.json" ]]; then
    export GOOGLE_APPLICATION_CREDENTIALS="/tmp/adc.json"
    echo "[entrypoint] Detected mounted ADC at /tmp/adc.json"
  elif [[ -f "/root/.config/gcloud/application_default_credentials.json" ]]; then
    export GOOGLE_APPLICATION_CREDENTIALS="/root/.config/gcloud/application_default_credentials.json"
    echo "[entrypoint] Detected ADC at /root/.config/gcloud/application_default_credentials.json"
  fi
else
  echo "[entrypoint] GOOGLE_APPLICATION_CREDENTIALS already set to ${GOOGLE_APPLICATION_CREDENTIALS}"
fi

echo "[entrypoint] Step 1/2: Optional GCS model download..."
if [[ -n "${GCS_MODEL_URI}" ]]; then
  echo "[entrypoint] GCS_MODEL_URI set -> downloading from bucket"
  python -m xplain_package.io.gcs
else
  echo "[entrypoint] No GCS_MODEL_URI set -> skipping download."
fi

echo "[entrypoint] Verifying local model folder..."
if [[ ! -d "${LOCAL_MODEL_DIR}" ]]; then
  echo "[entrypoint] ERROR: LOCAL_MODEL_DIR does not exist after download: ${LOCAL_MODEL_DIR}" >&2
  exit 1
fi
if [[ ! -f "${LOCAL_MODEL_DIR}/config.json" ]]; then
  echo "[entrypoint] ERROR: Missing config.json in ${LOCAL_MODEL_DIR}. Not a valid HF model folder." >&2
  exit 1
fi
echo "[entrypoint] Local model OK: ${LOCAL_MODEL_DIR}/config.json"

echo "[entrypoint] Step 2/2: Starting FastAPI..."
exec uvicorn api.fast:app --host 0.0.0.0 --port "${PORT}"
