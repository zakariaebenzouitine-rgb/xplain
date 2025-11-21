# ============================================================
# Dockerfile for XPLAIN (Inference-only)
#
# Goals:
# - Build a small image that runs FastAPI + BLIP inference
# - No training code in the image
# - Works with src/ package layout
# - Model weights are NOT baked in by default (gitignored)
#   -> container falls back to HF unless models/ is mounted
# ============================================================

# 1) Use a stable base Python version compatible with torch/transformers
#    (3.10 matches your Kaggle baseline and is safe for torch)
FROM python:3.10-slim

# 2) Set working directory inside the container
WORKDIR /app

# 3) Copy requirements file first (better Docker cache)
COPY requirements.txt /app/requirements.txt

# 4) Upgrade pip and install runtime dependencies
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# 5) Copy packaging metadata so "pip install ." works
COPY setup.py /app/setup.py
COPY README.md /app/README.md

# 6) Copy inference code (src-layout) + API
COPY src /app/src
COPY api /app/api

# 7) Install your package from src/
#    (not editable in Docker; clean install)
RUN pip install --no-cache-dir .

# 8) Expose port expected by Cloud Run / local docker
EXPOSE 8080
ENV PORT=8080

# 9) Start FastAPI
#    JSON CMD handles signals correctly
CMD ["uvicorn", "api.fast:app", "--host", "0.0.0.0", "--port", "8080"]
