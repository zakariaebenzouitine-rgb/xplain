"""
predict.py

Central inference entrypoints for the project.

This module MUST expose these functions because other files import them:

    - load_captioner()
    - predict_caption(image)      -> single image inference
    - predict_captions(images)    -> batch inference

Design goals:
- Offline-first: only load from LOCAL_MODEL_DIR or GCS_MODEL_URI.
- NO automatic HuggingFace fallback (to avoid "wrong model" surprises).
- Robust to future model changes via models.registry.get_model().
"""

from __future__ import annotations

import threading
from typing import List, Optional, Union

import torch
from PIL import Image

from xplain_package.config import settings          # global config (env-driven)
from xplain_package.models.registry import get_model
from xplain_package.preprocessing import preprocess_image
from xplain_package.utils.logging import get_logger

# ------------------------------------------------------------
# Logger for this module
# ------------------------------------------------------------
logger = get_logger(__name__)

# ------------------------------------------------------------
# Global cached objects
# We keep them in memory so:
#   - FastAPI startup loads once
#   - Requests reuse the model (fast)
# ------------------------------------------------------------
_MODEL = None
_PROCESSOR = None
_DEVICE = None

# A lock to avoid double-loading in parallel startup situations
_LOAD_LOCK = threading.Lock()


def load_captioner() -> None:
    """
    Load the model + processor ONCE and cache them globally.

    This is called:
    - at FastAPI startup
    - or lazily inside predict_* if someone forgot startup

    It uses get_model(settings) which:
    - loads from LOCAL_MODEL_DIR
    - OR downloads from GCS_MODEL_URI into LOCAL_MODEL_DIR (entrypoint)
    - and raises if nothing is there.

    NO HuggingFace fallback here.
    """
    global _MODEL, _PROCESSOR, _DEVICE

    if _MODEL is not None and _PROCESSOR is not None:
        # Already loaded: nothing to do
        return

    with _LOAD_LOCK:
        # Double-check inside lock
        if _MODEL is not None and _PROCESSOR is not None:
            return

        logger.info("Loading captioner (offline-only)…")

        # Device choice: GPU if available, else CPU
        _DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        logger.info(f"Using device: {_DEVICE}")

        # Get model wrapper from registry (future-proof)
        captioner = get_model(settings)

        # Extract actual HF objects
        _MODEL = captioner.model.to(_DEVICE)
        _PROCESSOR = captioner.processor

        # Put model in eval mode for inference
        _MODEL.eval()

        logger.info("Model loaded and cached successfully.")


@torch.no_grad()
def predict_caption(
    image: Union[Image.Image, bytes, str]
) -> str:
    """
    Predict a radiology explanation for ONE image.

    Parameters
    ----------
    image:
        - PIL.Image.Image
        - raw bytes (FastAPI UploadFile.read())
        - path string

    Returns
    -------
    text:
        A generated caption/explanation string.
    """
    # Ensure model is loaded
    load_captioner()

    # Preprocess input into a clean RGB PIL image
    pil_img = preprocess_image(image)

    # Convert to BLIP inputs (processor handles resize/normalize)
    inputs = _PROCESSOR(images=pil_img, return_tensors="pt")
    inputs = {k: v.to(_DEVICE) for k, v in inputs.items()}

    # Generate text
    generated_ids = _MODEL.generate(
        pixel_values=inputs["pixel_values"],
        max_new_tokens=settings.MAX_NEW_TOKENS,
        num_beams=settings.BEAM_SIZE,
        do_sample=False,  # deterministic
    )

    # Decode IDs into a string
    text = _PROCESSOR.batch_decode(
        generated_ids,
        skip_special_tokens=True
    )[0]

    return text.strip()


@torch.no_grad()
def predict_captions(
    images: List[Union[Image.Image, bytes, str]]
) -> List[str]:
    """
    Predict explanations for a BATCH of images.

    Parameters
    ----------
    images:
        list of images in any supported format.

    Returns
    -------
    texts:
        list of generated strings (same order as input).
    """
    # Ensure model is loaded
    load_captioner()

    # Preprocess each image to PIL RGB
    pil_images = [preprocess_image(img) for img in images]

    # Batch encoding
    inputs = _PROCESSOR(images=pil_images, return_tensors="pt")
    inputs = {k: v.to(_DEVICE) for k, v in inputs.items()}

    # Batch generation
    generated_ids = _MODEL.generate(
        pixel_values=inputs["pixel_values"],
        max_new_tokens=settings.MAX_NEW_TOKENS,
        num_beams=settings.BEAM_SIZE,
        do_sample=False,
    )

    # Decode batch
    texts = _PROCESSOR.batch_decode(
        generated_ids,
        skip_special_tokens=True
    )

    return [t.strip() for t in texts]
