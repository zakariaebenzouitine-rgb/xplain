"""
api/fast.py

FastAPI server for X-ray captioning.

Endpoints:
- GET  /             -> health check
- POST /predict      -> single image caption
- POST /predict_batch-> multiple images caption

The API stays thin and delegates real work to xplain_package.
"""

# FastAPI core objects
from fastapi import FastAPI, UploadFile, File, HTTPException

# We need tempfile to store uploads briefly
import tempfile

# os helps manage file paths and delete temp files
import os

# List is needed for typing multiple uploads
from typing import List

# Import inference helpers from our package
from xplain_package import load_captioner, predict_caption, predict_captions

# Create the FastAPI app
app = FastAPI(
    title="Xplain X-ray Captioning API",
    description="Inference-only API for BLIP chest X-ray explanations",
    version="0.2.0",
)

# ------------------------------------------------------------
# Startup event: load the model ONCE when the server starts
# ------------------------------------------------------------
@app.on_event("startup")
def startup_event():
    """
    Runs once when uvicorn starts.
    Loads the model into RAM and caches it.
    """
    load_captioner()


# ------------------------------------------------------------
# Health check route
# ------------------------------------------------------------
@app.get("/")
def root():
    """Simple health check."""
    return {"status": "ok", "message": "Xplain API is up"}


# ------------------------------------------------------------
# Single-image prediction route
# ------------------------------------------------------------
@app.post("/predict")
async def predict(file: UploadFile = File(...)):
    """
    Predict a caption from ONE uploaded X-ray image.

    Returns
    -------
    dict : {"caption": "..."}
    """

    tmp_path = None  # track temp file path for cleanup

    try:
        # Extract file extension
        suffix = os.path.splitext(file.filename)[1] or ".png"

        # Create temporary file
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            tmp.write(await file.read())
            tmp_path = tmp.name

        # Run inference
        caption = predict_caption(tmp_path)

        return {"caption": caption}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    finally:
        # Always remove temp file
        try:
            if tmp_path and os.path.exists(tmp_path):
                os.remove(tmp_path)
        except Exception:
            pass


# ------------------------------------------------------------
# Multi-image prediction route
# ------------------------------------------------------------
@app.post("/predict_batch")
async def predict_batch(files: List[UploadFile] = File(...)):
    """
    Predict captions from MULTIPLE uploaded X-ray images.

    Parameters
    ----------
    files : list[UploadFile]
        Several images uploaded together.

    Returns
    -------
    dict
        {
          "results": [
              {"filename": "...", "caption": "..."},
              ...
          ]
        }
    """

    # We will store temp paths here to clean them up later
    tmp_paths = []

    try:
        # 1) Save every uploaded file to a temp path
        for f in files:

            suffix = os.path.splitext(f.filename)[1] or ".png"

            with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
                tmp.write(await f.read())
                tmp_paths.append(tmp.name)

        # 2) Run batch inference using package helper
        captions = predict_captions(tmp_paths)

        # 3) Pair each caption with its original filename
        results = []
        for f, cap in zip(files, captions):
            results.append({
                "filename": f.filename,
                "caption": cap
            })

        return {"results": results}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    finally:
        # 4) Always clean up temp files
        for p in tmp_paths:
            try:
                if p and os.path.exists(p):
                    os.remove(p)
            except Exception:
                pass
