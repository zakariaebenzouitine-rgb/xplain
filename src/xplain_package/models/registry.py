"""
registry.py

Model registry / factory.

Goal:
- Keep the code robust if we switch model families later.
- Centralize model selection in ONE place.

🚨 IMPORTANT SAFETY CHANGE (NO INTERNET):
- We do NOT allow Hugging Face / online fallback anymore.
- Every model MUST be loaded from a LOCAL folder.
- "Bucket mode" works because entrypoint downloads the model
  from GCS into LOCAL_MODEL_DIR before FastAPI starts.

So the loading logic is:
    1) entrypoint.sh (optional) downloads GCS_MODEL_URI -> LOCAL_MODEL_DIR
    2) registry.py loads from LOCAL_MODEL_DIR strictly offline
"""

# ============================================================
# Standard library imports
# ============================================================

from typing import Any  # generic types for settings compatibility

# ============================================================
# Third-party imports
# ============================================================

import torch  # used only to detect device

# ============================================================
# Project imports
# ============================================================

from xplain_package.utils.logging import get_logger  # logger utility

# BLIP family (offline-only wrapper)
from xplain_package.models.blip import (
    BlipCaptioner,       # inference wrapper
    resolve_model_source # local model discovery (NO HF fallback)
)

# Create module logger
logger = get_logger(__name__)


# ============================================================
# Helper: device resolution
# ============================================================

def get_device(settings: Any) -> torch.device:
    """
    Decide which device to use.

    We keep this flexible because:
    - settings can change later
    - different machines may or may not have CUDA

    Priority:
    1) If settings.DEVICE exists, use it ("cpu" or "cuda")
    2) Else use CUDA if available
    3) Else CPU

    Parameters
    ----------
    settings : Any
        Settings object (from config.py). We use getattr to stay robust.

    Returns
    -------
    torch.device
        Torch device object.
    """

    # Try to use an explicit DEVICE from settings if present
    device_str = getattr(settings, "DEVICE", None)

    if device_str:
        # Respect explicit configuration
        return torch.device(device_str)

    # Otherwise auto-detect
    return torch.device("cuda" if torch.cuda.is_available() else "cpu")


# ============================================================
# Main factory: load the right model family
# ============================================================

def get_model(settings: Any):
    """
    Load the selected model family.

    🚫 NO INTERNET:
    - We do not use HF fallback.
    - We do not call from_pretrained with remote IDs.

    The ONLY valid source is LOCAL_MODEL_DIR,
    which may come from:
        - a folder already present in repo (local mode)
        - OR a downloaded GCS folder (cloud mode)

    Parameters
    ----------
    settings : Any
        Must contain at least:
            - MODEL_FAMILY (ex: "blip")
            - LOCAL_MODEL_DIR (ex: "models/cxiu_blip_baseline")

        HF_MODEL_NAME may exist for backward compatibility,
        but it is ignored.

    Returns
    -------
    model wrapper instance (e.g., BlipCaptioner)
    """

    # Read model family, default to "blip" if missing
    model_family = getattr(settings, "MODEL_FAMILY", "blip").lower()

    # Read local model dir (must be set)
    local_model_dir = getattr(settings, "LOCAL_MODEL_DIR", None)

    # Log what we are about to do
    logger.info(f"Model family requested: {model_family}")
    logger.info(f"Local model directory: {local_model_dir}")

    # Choose device
    device = get_device(settings)
    logger.info(f"Inference device: {device}")

    # ------------------------------------------------------------
    # BLIP FAMILY (offline only)
    # ------------------------------------------------------------
    if model_family == "blip":

        # Resolve to a real local pretrained folder
        # This raises if nothing valid is found.
        model_source = resolve_model_source(local_model_dir)

        # Load BLIP strictly from local files
        return BlipCaptioner.from_pretrained(
            model_source=model_source,
            device=device,
        )

    # ------------------------------------------------------------
    # Future families go here
    # ------------------------------------------------------------
    raise NotImplementedError(
        f"Unknown MODEL_FAMILY='{model_family}'. "
        "Supported families: ['blip']. "
        "If you add a new family, implement it here."
    )
