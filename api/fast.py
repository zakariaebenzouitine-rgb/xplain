"""
api/fast.py

FastAPI server for X-ray captioning.

This file is intentionally thin:
- It does NOT contain model logic.
- It simply calls the package inference function.

Endpoints:
- GET  /        -> health check
- POST /predict -> upload an image and get a caption

Later, this stays the same even if we change model family,
because predict_caption() is stable.
"""

# FastAPI core objects
from fastapi import FastAPI, UploadFile, File, HTTPException

# We need tempfile to safely store uploads for a moment
import tempfile

# os helps us manage file paths and delete temp files
import os

# Import inference helpers from our package
# - load_captioner(): loads model once at startup (cached)
# - predict_caption(path): runs BLIP on a saved image
from xplain_package import load_captioner, predict_caption

# Create the FastAPI app
app = FastAPI(
    title="Xplain X-ray Captioning API",
    description="Inference-only API for BLIP chest X-ray explanations",
    version="0.1.0",
)

# ------------------------------------------------------------
# Startup event: load the model ONCE when the server starts
# ------------------------------------------------------------
@app.on_event("startup")
def startup_event():
    """
    This runs a single time when uvicorn starts.

    We load the model here so:
    - first user request is fast
    - model stays in RAM (cached)
    """
    load_captioner()


# ------------------------------------------------------------
# Health check route
# ------------------------------------------------------------
@app.get("/")
def root():
    """
    Simple health check.
    Useful to verify the API is running.
    """
    return {"status": "ok", "message": "Xplain API is up"}


# ------------------------------------------------------------
# Prediction route
# ------------------------------------------------------------
@app.post("/predict")
async def predict(file: UploadFile = File(...)):
    """
    Predict a caption from an uploaded X-ray image.

    Parameters
    ----------
    file : UploadFile
        The uploaded image file.

    Returns
    -------
    dict
        {"caption": "..."} on success.
    """

    # We'll keep track of temp file path so we can delete it no matter what
    tmp_path = None

    try:
        # 1) Read original extension (png/jpg/etc).
        #    If missing, fallback to ".png"
        suffix = os.path.splitext(file.filename)[1] or ".png"

        # 2) Create a secure temporary file on disk
        #    delete=False because we want to close it first, then read it
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            # 3) Write uploaded bytes to disk
            tmp.write(await file.read())
            tmp_path = tmp.name

        # 4) Run inference using our package
        caption = predict_caption(tmp_path)

        # 5) Return JSON response
        return {"caption": caption}

    except Exception as e:
        # If anything fails, return a 500 with the error string
        raise HTTPException(status_code=500, detail=str(e))

    finally:
        # 6) Always clean up temp file
        try:
            if tmp_path and os.path.exists(tmp_path):
                os.remove(tmp_path)
        except Exception:
            # If cleanup fails, ignore (not critical)
            pass
