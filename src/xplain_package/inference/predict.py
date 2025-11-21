"""
predict.py

High-level inference functions.

This is the ONLY module the API (and coworkers) should use.

It provides:
- load_captioner(): loads & caches the model once
- predict_caption(image_path): returns caption for one image

Why caching?
- So FastAPI does NOT reload the BLIP model per request.
- Even locally, it avoids unnecessary reload time.
"""

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

    # Use the registry to load correct model family
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
        # Raise a clean project-level error
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
        max_length=settings.MAX_NEW_TOKENS if hasattr(settings, "MAX_NEW_TOKENS") else 128,
        num_beams=settings.BEAM_SIZE,
        do_sample=False  # keep deterministic for medical text
    )

    # -------------------------------
    # 6) Return text
    # -------------------------------
    return caption
