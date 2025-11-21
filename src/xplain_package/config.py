import os
from dataclasses import dataclass
from typing import Optional

@dataclass
class Settings:
    # --- model selection ---
    MODEL_FAMILY: str = os.getenv("MODEL_FAMILY", "blip")
    HF_MODEL_NAME: str = os.getenv(
        "HF_MODEL_NAME",
        "Salesforce/blip-image-captioning-base"
    )

    # --- local model cache / checkpoint name ---
    LOCAL_MODEL_DIR: str = os.getenv("LOCAL_MODEL_DIR", "models")
    MODEL_FILENAME: str = os.getenv("MODEL_FILENAME", "blip_captioning.pt")

    # Optional GCS (future use; no auth here)
    GCS_MODEL_URI: Optional[str] = os.getenv("GCS_MODEL_URI")  # gs://bucket/path.pt

    # --- inference ---
    DEVICE: str = os.getenv("DEVICE", "auto")  # auto | cpu | cuda
    MAX_NEW_TOKENS: int = int(os.getenv("MAX_NEW_TOKENS", "80"))
    BEAM_SIZE: int = int(os.getenv("BEAM_SIZE", "3"))

    # --- misc ---
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")

def get_settings() -> Settings:
    return Settings()
