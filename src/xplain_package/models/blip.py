"""
blip.py

Inference-only BLIP wrapper.

🚨 IMPORTANT SAFETY CHANGE (NO INTERNET):
- This project MUST NOT load models from Hugging Face Hub / the internet.
- It MUST load ONLY:
    1) from a LOCAL folder containing a finetuned BLIP save_pretrained(...)
    2) OR from a folder that was downloaded from GCS into LOCAL_MODEL_DIR.

Therefore:
- We set Hugging Face offline mode.
- We call from_pretrained(..., local_files_only=True).
- We REMOVE any HF fallback logic.
- If no valid local model is found -> we raise an error and crash startup.

Expected local folder structure (created by save_pretrained):
    <folder>/
        config.json
        pytorch_model.bin  OR model.safetensors
        preprocessor_config.json
        tokenizer_config.json (sometimes)
        ...
"""

# ============================================================
# Standard library imports
# ============================================================

import os  # for path checks and offline env vars
from dataclasses import dataclass  # convenient container for model + processor
from typing import List, Optional  # type hints for clarity

# ============================================================
# Third-party imports
# ============================================================

import torch  # device + no_grad inference
from transformers import BlipForConditionalGeneration, AutoProcessor  # BLIP baseline classes

# ============================================================
# Project imports
# ============================================================

from xplain_package.utils.logging import get_logger  # central logger helper


# ============================================================
# Global "OFFLINE" enforcement for Transformers / HF
# ============================================================
# These environment variables make Hugging Face libraries refuse network calls.
# Even if someone accidentally reintroduces HF fallback later,
# Transformers will not download anything.

os.environ["TRANSFORMERS_OFFLINE"] = "1"
os.environ["HF_DATASETS_OFFLINE"] = "1"

# Create logger for this module
logger = get_logger(__name__)


# ============================================================
# BLIP Wrapper
# ============================================================

@dataclass
class BlipCaptioner:
    """
    Small container around BLIP for caption generation.

    Attributes
    ----------
    processor : AutoProcessor
        Handles image preprocessing + decoding text outputs.
    model : BlipForConditionalGeneration
        Vision encoder + text decoder.
    device : torch.device
        CPU or GPU used for inference.
    """

    processor: AutoProcessor
    model: BlipForConditionalGeneration
    device: torch.device

    @classmethod
    def from_pretrained(
        cls,
        model_source: str,
        device: torch.device,
    ) -> "BlipCaptioner":
        """
        Load BLIP ONLY from a LOCAL folder.

        Parameters
        ----------
        model_source : str
            Path to the local folder containing config.json, weights, etc.
        device : torch.device
            "cpu" or "cuda"

        Returns
        -------
        BlipCaptioner
            Ready-to-use inference wrapper.

        Raises
        ------
        FileNotFoundError
            If model_source does not exist locally or is invalid.
        """

        # Log for transparency
        logger.info(f"Loading BLIP from local source ONLY: {model_source}")

        # Safety check: model_source must be a local directory
        if not os.path.isdir(model_source):
            raise FileNotFoundError(
                f"BLIP model folder not found locally: {model_source}. "
                "This project does NOT allow Hugging Face / internet loading."
            )

        # Processor loads ONLY from local folder
        processor = AutoProcessor.from_pretrained(
            model_source,
            local_files_only=True,   # 🚫 forbids downloading
            trust_remote_code=False  # extra safety
        )

        # Model loads ONLY from local folder
        model = BlipForConditionalGeneration.from_pretrained(
            model_source,
            local_files_only=True,   # 🚫 forbids downloading
            trust_remote_code=False
        )

        # Move model to chosen device (CPU/GPU)
        model.to(device)

        # Set inference mode
        model.eval()

        return cls(processor=processor, model=model, device=device)

    def generate(
        self,
        image,
        max_length: int = 128,
        num_beams: int = 3,
        do_sample: bool = False,
    ) -> str:
        """
        Generate a caption for ONE PIL image.

        Parameters
        ----------
        image : PIL.Image.Image
            Input X-ray (PIL object).
        max_length : int
            Maximum output tokens.
        num_beams : int
            Beam search width.
        do_sample : bool
            False = deterministic beam search (recommended for medical).

        Returns
        -------
        str
            Generated radiology explanation.
        """

        # Convert PIL image -> BLIP tensors
        encoding = self.processor(images=image, return_tensors="pt")

        # Move tensors to same device as model
        encoding = encoding.to(self.device)

        # Disable gradients for speed and memory
        with torch.no_grad():
            generated_ids = self.model.generate(
                pixel_values=encoding["pixel_values"],
                max_length=max_length,
                num_beams=num_beams,
                do_sample=do_sample,
            )

        # Decode tokens -> text
        generated_text = self.processor.batch_decode(
            generated_ids,
            skip_special_tokens=True
        )[0]

        return generated_text


# ============================================================
# Local model resolution (NO HF fallback)
# ============================================================

def resolve_model_source(
    local_model_dir: str,
    hf_model_name: Optional[str] = None,
) -> str:
    """
    Decide where to load the model from, STRICTLY locally.

    Rules:
    1) If local_model_dir is a valid pretrained folder (config.json exists),
       return it.
    2) If local_model_dir is a parent folder, search ONE level down for valid
       pretrained folders.
       - If exactly ONE is found, return it.
       - If multiple are found, raise (no guessing).
    3) If nothing valid locally, raise (NO HF fallback allowed).

    Parameters
    ----------
    local_model_dir : str
        Exact model folder OR parent folder.
    hf_model_name : Optional[str]
        Kept only for backward compatibility with old registry calls.
        It is NOT used anymore.

    Returns
    -------
    str
        A local folder path to pass into from_pretrained(...)

    Raises
    ------
    FileNotFoundError
        If no valid local pretrained model is found.
    RuntimeError
        If multiple valid models are found (ambiguous).
    """

    # If no local dir provided, this is a fatal configuration error
    if not local_model_dir:
        raise FileNotFoundError(
            "LOCAL_MODEL_DIR is empty. "
            "Set it to a local folder containing your finetuned BLIP model."
        )

    # ------------------------------------------------------------
    # Case 1) local_model_dir is already a pretrained folder
    # ------------------------------------------------------------
    config_path = os.path.join(local_model_dir, "config.json")

    if os.path.isdir(local_model_dir) and os.path.isfile(config_path):
        logger.info(
            f"Local model directory looks valid (config.json found): {local_model_dir}"
        )
        return local_model_dir

    # ------------------------------------------------------------
    # Case 2) local_model_dir is parent folder -> search children
    # ------------------------------------------------------------
    if os.path.isdir(local_model_dir):

        # List everything inside parent folder
        children = os.listdir(local_model_dir)

        # Look for child folders containing config.json
        candidate_folders: List[str] = []

        for child in children:
            child_path = os.path.join(local_model_dir, child)
            child_config = os.path.join(child_path, "config.json")

            if os.path.isdir(child_path) and os.path.isfile(child_config):
                candidate_folders.append(child_path)

        # Exactly one valid model -> choose it
        if len(candidate_folders) == 1:
            chosen = candidate_folders[0]
            logger.info(
                f"Found one valid pretrained model folder inside "
                f"{local_model_dir}: {chosen}"
            )
            return chosen

        # Multiple valid models -> ambiguous, crash
        if len(candidate_folders) > 1:
            raise RuntimeError(
                f"Multiple pretrained model folders found inside {local_model_dir}: "
                f"{candidate_folders}. "
                f"Set LOCAL_MODEL_DIR to the exact folder you want."
            )

    # ------------------------------------------------------------
    # Case 3) nothing valid locally -> fatal error (NO HF)
    # ------------------------------------------------------------
    raise FileNotFoundError(
        f"No valid local pretrained model found in: {local_model_dir}. "
        "HF / internet fallback is disabled. "
        "Either mount your models folder OR set GCS_MODEL_URI so entrypoint downloads it."
    )
