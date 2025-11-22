"""
xplain_package/config.py

Central configuration for XPLAIN.

Design goals:
- No network/model downloads happen here.
- All defaults are safe for local dev.
- Provide BOTH a singleton `settings` and a backward-compatible `get_settings()`
  so any module can import either without breaking.
"""

import os
from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class Settings:
    # --- model family selection ---
    MODEL_FAMILY: str = os.getenv("MODEL_FAMILY", "blip")

    # Hugging Face fallback name (used only if ALLOW_HF_FALLBACK=true)
    HF_MODEL_NAME: str = os.getenv(
        "HF_MODEL_NAME",
        "Salesforce/blip-image-captioning-base"
    )

    # --- local model path inside container/repo ---
    LOCAL_MODEL_DIR: str = os.getenv("LOCAL_MODEL_DIR", "models")
    MODEL_FILENAME: str = os.getenv("MODEL_FILENAME", "blip_captioning.pt")

    # Optional GCS URI prefix (folder or file).
    # Example: gs://bucket/models/cxiu_blip_baseline
    GCS_MODEL_URI: Optional[str] = os.getenv("GCS_MODEL_URI") or None

    # HF fallback gate (default false for offline safety)
    ALLOW_HF_FALLBACK: bool = os.getenv("ALLOW_HF_FALLBACK", "false").lower() == "true"

    # --- inference ---
    DEVICE: str = os.getenv("DEVICE", "auto")  # auto | cpu | cuda
    MAX_NEW_TOKENS: int = int(os.getenv("MAX_NEW_TOKENS", "80"))
    BEAM_SIZE: int = int(os.getenv("BEAM_SIZE", "3"))

    # --- misc ---
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")


# Singleton settings object
settings = Settings()


def get_settings() -> Settings:
    """Backward-compatible accessor."""
    return settings
