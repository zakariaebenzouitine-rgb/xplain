"""
predict.py

High-level inference functions.

This is the ONLY module the API (and coworkers) should use.

It provides:
- load_captioner(): loads & caches the model once
- predict_caption(image_path): returns caption for one image
- predict_captions(image_paths): returns captions for many images

Why caching?
- So FastAPI does NOT reload the BLIP model per request.
- Even locally, it avoids unnecessary reload time.
"""

# -------------------------------
# Imports
# -------------------------------

# Import central settings (env-configurable)
from xplain_package.config import get_settings

# Import safe image loader
from xplain_package.data.transforms import load_image

# Import model registry (picks BLIP + device + local/HF source)
from xplain_package.models.registry import get_model

# Logger for clean debug messages
from xplain_package.utils.logging import get_logger

# Custom clean error for user-facing mistakes
from xplain_package.utils.exceptions import InvalidInputError

# Create a logger for this module
logger = get_logger(__name__)

# ------------------------------------------------------------
# Model cache (module-level global)
# ------------------------------------------------------------
# We keep one model instance in memory after first load.
# This is perfect for FastAPI startup and repeated inference.
_MODEL = None


def load_captioner():
    """
    Load the captioning model ONCE and keep it in memory.

    Returns
    -------
    BlipCaptioner (or future model wrapper)
        A ready-to-use model wrapper.
    """

    global _MODEL

    # If we already loaded the model earlier, reuse it.
    if _MODEL is not None:
        return _MODEL

    # Otherwise, load configuration from env vars or defaults
    settings = get_settings()

    # Use registry to load correct model family
    _MODEL = get_model(settings)

    # Log success
    logger.info("Model loaded and cached successfully.")

    return _MODEL


def predict_caption(image_path: str) -> str:
    """
    Generate a radiology explanation for ONE X-ray image.

    Parameters
    ----------
    image_path : str
        Path to a local image file.

    Returns
    -------
    str
        Generated caption (radiology explanation).
    """

    # -------------------------------
    # 1) Validate input
    # -------------------------------
    if not image_path:
        raise InvalidInputError("image_path is empty. Provide a valid image path.")

    # -------------------------------
    # 2) Load model (cached)
    # -------------------------------
    captioner = load_captioner()

    # -------------------------------
    # 3) Load image safely
    # -------------------------------
    image = load_image(image_path)

    # -------------------------------
    # 4) Read inference settings
    # -------------------------------
    settings = get_settings()

    # -------------------------------
    # 5) Generate caption
    # -------------------------------
    caption = captioner.generate(
        image=image,
        max_length=(
            settings.MAX_NEW_TOKENS
            if hasattr(settings, "MAX_NEW_TOKENS")
            else 128
        ),
        num_beams=settings.BEAM_SIZE,
        do_sample=False  # deterministic is better for medical text
    )

    # -------------------------------
    # 6) Return text
    # -------------------------------
    return caption


def predict_captions(image_paths):
    """
    Generate radiology explanations for MULTIPLE X-ray images.

    Parameters
    ----------
    image_paths : list[str]
        List of paths to local image files.

    Returns
    -------
    list[str]
        List of captions in the SAME order as image_paths.
    """

    # -------------------------------
    # 1) Validate input list
    # -------------------------------
    if image_paths is None or len(image_paths) == 0:
        raise InvalidInputError("image_paths is empty. Provide at least one image path.")

    # -------------------------------
    # 2) Load model ONCE (cached)
    # -------------------------------
    captioner = load_captioner()

    # -------------------------------
    # 3) Read inference settings ONCE
    # -------------------------------
    settings = get_settings()

    # -------------------------------
    # 4) Loop over images, generate captions
    # -------------------------------
    captions = []

    for path in image_paths:

        # Make sure each path is valid
        if not path:
            raise InvalidInputError("One of the image paths is empty.")

        # Load PIL image from disk
        image = load_image(path)

        # Generate caption using same settings for all
        caption = captioner.generate(
            image=image,
            max_length=(
                settings.MAX_NEW_TOKENS
                if hasattr(settings, "MAX_NEW_TOKENS")
                else 128
            ),
            num_beams=settings.BEAM_SIZE,
            do_sample=False
        )

        # Add to output list
        captions.append(caption)

    # -------------------------------
    # 5) Return all captions
    # -------------------------------
    return captions
