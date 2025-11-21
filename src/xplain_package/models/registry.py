"""
registry.py

This file acts like a "model router".

The rest of the project will call ONLY:
    get_model(settings)

And this registry will:
1) decide CPU vs GPU automatically
2) decide whether to load from local folder or HF hub
3) return the correct model wrapper (BLIP for now)

If we change to another model later, we add a new wrapper and
just extend get_model(...) with another branch.
"""

# We need torch to manage devices (cpu/cuda) and check GPU availability
import torch

# Import the Settings dataclass from config
from xplain_package.config import Settings

# Import BLIP wrapper + helper to choose local vs HF source
from xplain_package.models.blip import BlipCaptioner, resolve_model_source


def resolve_device(device_setting: str) -> torch.device:
    """
    Convert a string device setting into a torch.device.

    Parameters
    ----------
    device_setting : str
        Either:
        - "auto"  -> use GPU if available, else CPU
        - "cpu"   -> force CPU
        - "cuda"  -> force GPU (will crash if no GPU)

    Returns
    -------
    torch.device
        The device to use for inference.
    """

    # If user wants automatic device selection:
    if device_setting == "auto":
        # Check if a CUDA GPU is available
        if torch.cuda.is_available():
            return torch.device("cuda")
        # Otherwise use CPU
        return torch.device("cpu")

    # If user explicitly set "cpu" or "cuda", trust them
    return torch.device(device_setting)


def get_model(settings: Settings):
    """
    Main entrypoint for loading a model.

    Parameters
    ----------
    settings : Settings
        Central configuration object (from config.py).

    Returns
    -------
    Any model wrapper (currently BlipCaptioner).
    """

    # 1) Choose device based on settings
    device = resolve_device(settings.DEVICE)

    # 2) Decide where model loads from:
    #    - if local folder exists -> use it
    #    - else -> use HF model id
    model_source = resolve_model_source(
        local_model_dir=settings.LOCAL_MODEL_DIR,
        hf_model_name=settings.HF_MODEL_NAME,
    )

    # 3) Pick model family (for now only BLIP)
    if settings.MODEL_FAMILY.lower() == "blip":
        # Load BLIP from local folder or HF hub
        return BlipCaptioner.from_pretrained(
            model_source=model_source,
            device=device
        )

    # 4) If model family is unknown, raise a clear error
    raise ValueError(
        f"Unknown MODEL_FAMILY: {settings.MODEL_FAMILY}. "
        "Supported families: ['blip']"
    )
