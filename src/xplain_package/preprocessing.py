"""
preprocessing.py

Inference-time preprocessing only.

Important:
- We DO NOT do any heavy preprocessing for BLIP.
- BLIP's HuggingFace processor handles resizing/normalization.
- We only need to make sure the input is a valid PIL RGB image.

This file must expose:
    preprocess_image(...)
because predict.py imports that exact name.
"""

from __future__ import annotations

import io
from pathlib import Path
from typing import Union

import numpy as np
from PIL import Image

# OpenCV is optional here, but safe to import because we use
# opencv-python-headless in requirements.txt
import cv2


def preprocess_image(image: Union[Image.Image, bytes, str, Path]) -> Image.Image:
    """
    Convert various input types into a clean PIL RGB image.

    Supported inputs:
    - PIL.Image.Image (already loaded)
    - bytes (raw file bytes, e.g. UploadFile.read())
    - str / Path (path to an image on disk)

    What we do:
    1) Load / decode image if needed
    2) Convert to RGB (BLIP expects 3 channels)
    3) Return PIL image (no resizing here)

    We keep this minimal to stay robust if the model changes later.
    """

    # ------------------------------------------------------------
    # 1) If input is already a PIL image, keep it
    # ------------------------------------------------------------
    if isinstance(image, Image.Image):
        pil_img = image

    # ------------------------------------------------------------
    # 2) If input is raw bytes, decode with PIL
    # ------------------------------------------------------------
    elif isinstance(image, (bytes, bytearray)):
        pil_img = Image.open(io.BytesIO(image))

    # ------------------------------------------------------------
    # 3) If input is a path, load from disk
    # ------------------------------------------------------------
    elif isinstance(image, (str, Path)):
        pil_img = Image.open(str(image))

    else:
        raise TypeError(
            "preprocess_image received unsupported type. "
            "Expected PIL.Image, bytes, str, or Path."
        )

    # ------------------------------------------------------------
    # Some X-rays are stored as grayscale ("L") or RGBA.
    # BLIP wants RGB, so we force conversion here.
    # ------------------------------------------------------------
    pil_img = pil_img.convert("RGB")

    return pil_img


def pil_to_cv2(pil_img: Image.Image) -> np.ndarray:
    """
    Utility: Convert PIL RGB image to OpenCV BGR numpy array.

    Not required by BLIP, but handy for future preprocessing.
    """
    rgb = np.array(pil_img)
    bgr = cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)
    return bgr


def cv2_to_pil(cv2_img: np.ndarray) -> Image.Image:
    """
    Utility: Convert OpenCV BGR numpy array to PIL RGB image.

    Not required by BLIP, but handy for future preprocessing.
    """
    rgb = cv2.cvtColor(cv2_img, cv2.COLOR_BGR2RGB)
    pil_img = Image.fromarray(rgb)
    return pil_img
