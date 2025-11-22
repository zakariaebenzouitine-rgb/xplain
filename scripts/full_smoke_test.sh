#!/usr/bin/env bash
set -euo pipefail

# ============================================================
# full_smoke_test.sh
#
# End-to-end smoke tests for XPLAIN:
# 1) Local uvicorn (LOCAL model only)
# 2) Local docker (LOCAL model only)
# 3) Local docker (BUCKET model only)
# 4) Cloud Run tests (optional)
#
# Each step temporarily OVERRIDES env vars so we test
# the exact intended loading path every time.
# ============================================================

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

TS="$(date +%Y%m%d-%H%M%S)"

ENV_FILE="$ROOT_DIR/.env"
ENV_YAML="$ROOT_DIR/.env.yaml"

ENV_FILE_BAK="$ROOT_DIR/.env.bak.$TS"
ENV_YAML_BAK="$ROOT_DIR/.env.yaml.bak.$TS"

SAMPLE1="$ROOT_DIR/raw_data/sample.png"
SAMPLE2="$ROOT_DIR/raw_data/sample2.png"

DOCKER_IMAGE="${DOCKER_IMAGE_NAME:-api}:local"
DOCKER_PORT="${DOCKER_LOCAL_PORT:-8080}"
UVICORN_PORT="${UVICORN_PORT:-8000}"

LOCAL_MODEL_DIR_DEFAULT="${LOCAL_MODEL_DIR:-models/cxiu_blip_baseline}"
GCS_MODEL_URI_DEFAULT="${GCS_MODEL_URI:-}"

GCP_PROJECT_DEFAULT="${GCP_PROJECT:-${GOOGLE_CLOUD_PROJECT:-}}"
GCP_REGION_DEFAULT="${GCP_REGION:-europe-west1}"

ADC_HOST_PATH="$HOME/.config/gcloud/application_default_credentials.json"

# -----------------------------
# helpers
# -----------------------------
log_step () {
  echo ""
  echo "========== $1 =========="
}

backup_file () {
  local f="$1" bak="$2"
  if [[ -f "$f" ]]; then
    cp "$f" "$bak"
    echo "[OK] Backup created for $(basename "$f")"
  else
    echo "[WARN] $(basename "$f") not found -> no backup"
  fi
}

restore_file () {
  local f="$1" bak="$2"
  if [[ -f "$bak" ]]; then
    cp "$bak" "$f"
    echo "[OK] Restored $(basename "$f") from $(basename "$bak")"
  fi
}

wait_url () {
  local url="$1"
  local timeout="${2:-1200}"  # seconds
  local waited=0

  while true; do
    if curl -s -o /dev/null -w "%{http_code}" "$url" | grep -qE "^(200|404)$"; then
      echo "[OK] Ready: $url returned $(curl -s -o /dev/null -w "%{http_code}" "$url")"
      return 0
    fi
    sleep 5
    waited=$((waited+5))
    echo "[wait] $url not ready yet... (${waited}s/${timeout}s)"
    if (( waited >= timeout )); then
      echo "[FAIL] Timeout waiting for $url"
      return 1
    fi
  done
}

post_predict () {
  local base="$1"
  local img="$2"

  echo ""
  echo "[TEST] POST ${base}/predict using $img"
  curl -s -X POST "${base}/predict" \
    -F "file=@${img}" \
    | tee /dev/stderr \
    | grep -qi "caption" \
    && echo "[OK] /predict OK" \
    || { echo "[FAIL] /predict failed"; return 1; }
}

post_predict_batch () {
  local base="$1"
  local img1="$2"
  local img2="$3"

  echo ""
  echo "[TEST] POST ${base}/predict_batch using: $img1,$img2"
  curl -s -X POST "${base}/predict_batch" \
    -F "files=@${img1}" \
    -F "files=@${img2}" \
    | tee /dev/stderr \
    | grep -qi "results" \
    && echo "[OK] /predict_batch OK" \
    || { echo "[FAIL] /predict_batch failed"; return 1; }
}

cleanup_docker () {
  local cid="$1"
  if [[ -n "$cid" ]]; then
    docker rm -f "$cid" >/dev/null 2>&1 || true
    echo "[OK] Stopped docker container"
  fi
}

cleanup_uvicorn () {
  local pid="$1"
  if [[ -n "$pid" ]]; then
    kill "$pid" >/dev/null 2>&1 || true
    echo "[OK] Stopped local uvicorn"
  fi
}

# trap restores env even on fail
UVICORN_PID=""
DOCKER_CID=""
BUCKET_CID=""
TMP_BUCKET_MODELS=""

on_exit () {
  echo ""
  echo "Cleaning up..."
  cleanup_uvicorn "$UVICORN_PID"
  cleanup_docker "$DOCKER_CID"
  cleanup_docker "$BUCKET_CID"
  [[ -n "$TMP_BUCKET_MODELS" ]] && rm -rf "$TMP_BUCKET_MODELS" || true

  restore_file "$ENV_FILE" "$ENV_FILE_BAK"
  restore_file "$ENV_YAML" "$ENV_YAML_BAK"

  echo "Done cleanup."
}
trap on_exit EXIT

# -----------------------------
# STEP 0: backups
# -----------------------------
log_step "STEP 0: Back up config files"
backup_file "$ENV_FILE" "$ENV_FILE_BAK"
backup_file "$ENV_YAML" "$ENV_YAML_BAK"

# -----------------------------
# STEP 1: preflight checks
# -----------------------------
log_step "STEP 1: Pre-flight checks"

python -c "import xplain_package; print('IMPORT OK:', xplain_package.__file__)"
python - <<'PY'
from xplain_package.inference import predict
assert hasattr(predict, "load_captioner")
assert hasattr(predict, "predict_caption")
assert hasattr(predict, "predict_captions")
print("PREDICT EXPORTS OK")
PY
echo "[OK] Package exports OK"

if [[ ! -f "$SAMPLE1" ]]; then
  echo "[WARN] $SAMPLE1 missing; predict tests may fail."
fi
if [[ ! -f "$SAMPLE2" ]]; then
  echo "[WARN] $SAMPLE2 missing; batch tests may fail."
fi

if [[ -f "$ROOT_DIR/$LOCAL_MODEL_DIR_DEFAULT/config.json" ]]; then
  echo "[OK] Local finetuned model looks valid"
else
  echo "[WARN] Local model folder missing config.json"
fi

if [[ -n "$GCS_MODEL_URI_DEFAULT" ]]; then
  echo "[OK] Detected GCS_MODEL_URI: $GCS_MODEL_URI_DEFAULT"
else
  echo "[WARN] No GCS_MODEL_URI found -> bucket tests may be skipped."
fi

# -----------------------------
# STEP 2: uvicorn local (LOCAL only)
# -----------------------------
log_step "STEP 2: Local uvicorn with LOCAL model (GCS OFF, HF OFF)"

export MODEL_FAMILY="${MODEL_FAMILY:-blip}"
export LOCAL_MODEL_DIR="$LOCAL_MODEL_DIR_DEFAULT"
export GCS_MODEL_URI=""
export ALLOW_HF_FALLBACK="false"
export PORT="$UVICORN_PORT"

uvicorn api.fast:app --host 127.0.0.1 --port "$UVICORN_PORT" >/tmp/xplain_uvicorn.log 2>&1 &
UVICORN_PID=$!

wait_url "http://127.0.0.1:${UVICORN_PORT}/"

# /health is 404 on your API; ok
if curl -s -o /dev/null -w "%{http_code}" "http://127.0.0.1:${UVICORN_PORT}/health" | grep -q "^404$"; then
  echo "[WARN] /health returns 404 on this API. Script continues using other endpoints."
fi

post_predict "http://127.0.0.1:${UVICORN_PORT}" "$SAMPLE1"
post_predict_batch "http://127.0.0.1:${UVICORN_PORT}" "$SAMPLE1" "$SAMPLE2"
echo "[OK] Local uvicorn tests passed"

cleanup_uvicorn "$UVICORN_PID"
UVICORN_PID=""

# -----------------------------
# STEP 3: docker local (LOCAL only)
# -----------------------------
log_step "STEP 3: Local docker with LOCAL model (GCS OFF, HF OFF)"

# Force local-only inside container
DOCKER_CID=$(docker run -d --rm \
  -e PORT=8080 \
  -e MODEL_FAMILY="${MODEL_FAMILY:-blip}" \
  -e LOCAL_MODEL_DIR="$LOCAL_MODEL_DIR_DEFAULT" \
  -e GCS_MODEL_URI="" \
  -e ALLOW_HF_FALLBACK="false" \
  -p "${DOCKER_PORT}:8080" \
  --env-file "$ENV_FILE" \
  -v "$ROOT_DIR/models:/app/models:ro" \
  "$DOCKER_IMAGE")

echo "[OK] Docker container started: $DOCKER_CID"

if ! wait_url "http://127.0.0.1:${DOCKER_PORT}/"; then
  echo "[FAIL] Docker local model container not ready."
  echo "---- last logs ----"
  docker logs "$DOCKER_CID" || true
  exit 1
fi

post_predict "http://127.0.0.1:${DOCKER_PORT}" "$SAMPLE1"
post_predict_batch "http://127.0.0.1:${DOCKER_PORT}" "$SAMPLE1" "$SAMPLE2"
echo "[OK] Local docker (LOCAL model) tests passed"

cleanup_docker "$DOCKER_CID"
DOCKER_CID=""

# -----------------------------
# STEP 4: docker local (BUCKET only)
# -----------------------------
log_step "STEP 4: Local docker with BUCKET model (LOCAL OFF, HF OFF)"

if [[ -z "$GCS_MODEL_URI_DEFAULT" ]]; then
  echo "[SKIP] No GCS_MODEL_URI -> skipping bucket-only docker test."
else
  TMP_BUCKET_MODELS="$(mktemp -d)"
  echo "[INFO] Using empty temp models dir: $TMP_BUCKET_MODELS"

  ADC_MOUNT=()
  if [[ -f "$ADC_HOST_PATH" ]]; then
    echo "[INFO] Found host ADC at $ADC_HOST_PATH -> mounting into container"
    ADC_MOUNT=(-v "$ADC_HOST_PATH:/tmp/adc.json:ro" -e GOOGLE_APPLICATION_CREDENTIALS=/tmp/adc.json)
  else
    echo "[WARN] No host ADC found. Bucket test will likely fail unless bucket is public."
  fi

  BUCKET_CID=$(docker run -d --rm \
    -e PORT=8080 \
    -e MODEL_FAMILY="${MODEL_FAMILY:-blip}" \
    -e LOCAL_MODEL_DIR="$LOCAL_MODEL_DIR_DEFAULT" \
    -e GCS_MODEL_URI="$GCS_MODEL_URI_DEFAULT" \
    -e ALLOW_HF_FALLBACK="false" \
    -e GOOGLE_CLOUD_PROJECT="$GCP_PROJECT_DEFAULT" \
    -p "${DOCKER_PORT}:8080" \
    --env-file "$ENV_FILE" \
    -v "$TMP_BUCKET_MODELS:/app/models" \
    "${ADC_MOUNT[@]}" \
    "$DOCKER_IMAGE")

  echo "[OK] Docker container started (bucket mode): $BUCKET_CID"

  if ! wait_url "http://127.0.0.1:${DOCKER_PORT}/"; then
    echo "[FAIL] Bucket-only docker container not ready."
    echo "---- last logs ----"
    docker logs "$BUCKET_CID" || true
    exit 1
  fi

  post_predict "http://127.0.0.1:${DOCKER_PORT}" "$SAMPLE1"
  post_predict_batch "http://127.0.0.1:${DOCKER_PORT}" "$SAMPLE1" "$SAMPLE2"
  echo "[OK] Local docker (BUCKET model) tests passed"

  cleanup_docker "$BUCKET_CID"
  BUCKET_CID=""
fi

# -----------------------------
# STEP 5: Cloud Run tests (optional)
# -----------------------------
log_step "STEP 5: Cloud Run tests (optional)"

if [[ "${RUN_CLOUD_TESTS:-0}" == "1" ]]; then
  if [[ -z "${XPLAIN_CLOUD_URL:-}" ]]; then
    echo "[FAIL] RUN_CLOUD_TESTS=1 but XPLAIN_CLOUD_URL not set."
    exit 1
  fi

  echo "[OK] Cloud URL: $XPLAIN_CLOUD_URL"
  wait_url "$XPLAIN_CLOUD_URL/"
  echo "[OK] Cloud ready"

  post_predict "$XPLAIN_CLOUD_URL" "$SAMPLE1"
  post_predict_batch "$XPLAIN_CLOUD_URL" "$SAMPLE1" "$SAMPLE2"
  echo "[OK] Cloud Run predict tests passed"
else
  echo "[SKIP] Cloud tests disabled (set RUN_CLOUD_TESTS=1 to enable)."
fi

echo ""
echo "✅ ALL REQUESTED SMOKE TESTS COMPLETED SUCCESSFULLY"
