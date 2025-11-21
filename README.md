# XPLAIN — Chest X-ray Captioning (Inference Package)

XPLAIN is an inference-only project that generates radiology explanations from chest X-ray images using a finetuned BLIP baseline.

**Key principles**
- ✅ Inference only (no training code in this repo)
- ✅ Run locally or in Docker
- ✅ Robust to future model swaps
- ✅ Optional model download from GCS at container startup
- ✅ No credentials or auth logic stored in the repo

---

## Project structure (important parts)

api/fast.py # FastAPI app with /predict + /predict_batch
src/xplain_package/ # Python package (inference logic)
models/ # root weights folder (ignored in git)
scripts/entrypoint.sh # Docker startup hook (GCS download -> uvicorn)
scripts/deploy_cloud_run.sh # future Cloud Run deploy wrapper
scripts/bootstrap_artifact_registry.sh # future Artifact Registry setup
DEPLOYMENT_CHECKLIST.md # future deployment recipe


---

## Requirements

- Python 3.10+
- GPU optional (CPU works, slower)

---

## Local installation (no Docker)

```bash
# 1) Create venv
python -m venv .venv
source .venv/bin/activate

# 2) Install runtime deps + package
make install_requirements
pip install -e .

# 3) Create .env
cp .env.example .env


-------------------


Put your finetuned baseline locally (recommended)

Place the model folder here:

models/cxiu_blip_baseline/
  config.json
  pytorch_model.bin
  preprocessor_config.json
  tokenizer_config.json
  special_tokens_map.json
  ...


Then set in .env:

MODEL_FAMILY=blip
LOCAL_MODEL_DIR=models/cxiu_blip_baseline
HF_MODEL_NAME=Salesforce/blip-image-captioning-base
BEAM_SIZE=3
MAX_NEW_TOKENS=128


Run FastAPI locally
make run_api


Open Swagger:

http://127.0.0.1:8000/docs

Docker usage (local test)
Build
make docker_build_local

Run (with local weights mounted)
docker run --rm \
  -p 8080:8080 \
  --env-file .env \
  -v $(pwd)/models:/app/models \
  api:local


Swagger:

http://127.0.0.1:8080/docs

How inference works

On API startup, load_captioner() loads the BLIP captioner.

If LOCAL_MODEL_DIR contains a valid finetuned model, it is loaded.

Otherwise it falls back to HF_MODEL_NAME (BLIP base from Hugging Face).

Endpoints:

POST /predict → one image caption

POST /predict_batch → multiple images captioned in one call

Switching model later (minimal edits)

To change model in the future:

Upload new model folder to GCS (or local)

Change only env vars:

MODEL_FAMILY=<new_family_if_needed>
GCS_MODEL_URI=gs://bucket/new_model_folder   # optional
LOCAL_MODEL_DIR=models/new_model_folder
HF_MODEL_NAME=<hf_fallback_name>


If preprocessing changes are required:
edit src/xplain_package/data/transforms.py

If model family is new:
add wrapper in src/xplain_package/models/
and register it in registry.py


Dev / notebook setup (optional)

Runtime deps are in requirements.txt.

Dev deps (notebooks, tests, linting) are optional:

pip install -U pip setuptools wheel
pip install -e ".[dev]"


Deployment (future)

This repo is already prepared for Cloud Run deployment:

Model can be downloaded from GCS at container startup via GCS_MODEL_URI

No credentials are stored in code

Deployment steps are documented in:

DEPLOYMENT_CHECKLIST.md

Troubleshooting

No module named xplain_package

pip install -e .


Docker can’t find model
Run with volume mount:

-v $(pwd)/models:/app/models


Model folder missing
Ask teammate for baseline weights zip.
Weights are intentionally not committed.

License / credits

Baseline: Salesforce/blip-image-captioning-base
