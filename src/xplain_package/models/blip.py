"""
blip.py

Inference-only BLIP wrapper.

This matches your Kaggle baseline exactly:
- Model class: BlipForConditionalGeneration
- Processor class: AutoProcessor
- Saved via:
      model.save_pretrained(OUTPUT_DIR)
      processor.save_pretrained(OUTPUT_DIR)

Important:
- BLIP expects a *folder* with config.json, pytorch_model.bin, etc.
- NOT a single .pt file.
"""

# Standard library import
import os  # used to check local folders and files

# Dataclass = clean way to store processor + model + device together
from dataclasses import dataclass

# PyTorch handles GPU/CPU device placement and no_grad inference
import torch

# Hugging Face BLIP baseline classes (same as your notebook)
from transformers import BlipForConditionalGeneration, AutoProcessor

# Project logger helper
from xplain_package.utils.logging import get_logger

# Create logger for this module
logger = get_logger(__name__)


@dataclass
class BlipCaptioner:
    """
    Small container around BLIP for caption generation.

    Attributes
    ----------
    processor : AutoProcessor
        Handles image preprocessing + text decoding.
    model : BlipForConditionalGeneration
        Vision encoder + text decoder.
    device : torch.device
        CPU or GPU where inference runs.
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
        Load BLIP either from:
        - LOCAL folder saved with save_pretrained(...)
        - OR Hugging Face hub id.

        Parameters
        ----------
        model_source : str
            Example local folder:
                "models/cxiu_blip_baseline"
            Example HF hub id:
                "Salesforce/blip-image-captioning-base"
        device : torch.device
            "cpu" or "cuda"

        Returns
        -------
        BlipCaptioner
            Ready-to-use inference wrapper.
        """

        # Log for transparency
        logger.info(f"Loading BLIP from: {model_source}")

        # Processor loads from local folder OR HF hub
        processor = AutoProcessor.from_pretrained(model_source)

        # Model loads from local folder OR HF hub
        model = BlipForConditionalGeneration.from_pretrained(model_source)

        # Move model to the chosen device
        model.to(device)

        # Eval mode = inference only (no dropout)
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
            Maximum total output length.
            (Aligns with Kaggle MAX_LENGTH.)
        num_beams : int
            Beam width (you used 3 for best outputs).
        do_sample : bool
            False = deterministic beam search (recommended for medical).
            True  = random sampling (more creative but less stable).

        Returns
        -------
        str
            Radiology explanation / caption.
        """

        # Convert PIL image into model tensors
        encoding = self.processor(images=image, return_tensors="pt")

        # Move tensors to same device as model
        encoding = encoding.to(self.device)

        # Disable gradients for speed & memory safety
        with torch.no_grad():

            # Generate output token IDs
            generated_ids = self.model.generate(
                pixel_values=encoding["pixel_values"],  # BLIP expects pixel_values
                max_length=max_length,
                num_beams=num_beams,
                do_sample=do_sample,
            )

        # Decode IDs to text
        generated_text = self.processor.batch_decode(
            generated_ids,
            skip_special_tokens=True
        )[0]  # batch size = 1

        return generated_text


def resolve_model_source(
    local_model_dir: str,
    hf_model_name: str,
) -> str:
    """
    Decide where to load the model from.

    Robust logic:

    1) If local_model_dir itself looks like a HF "save_pretrained" folder
       (contains config.json), load from there.

    2) If local_model_dir is only a parent folder (e.g. "models/"),
       search ONE level down for subfolders that contain config.json.
       - If exactly ONE is found, load from it.
       - If multiple are found, don't guess -> fallback to HF.

    3) If nothing valid locally, fallback to HF model id.

    Parameters
    ----------
    local_model_dir : str
        Could be:
        - exact model folder
        - OR parent directory containing model folder
    hf_model_name : str
        HF fallback (Salesforce/blip-image-captioning-base)

    Returns
    -------
    str
        A path or HF hub id to pass to from_pretrained(...)
    """

    # If no local dir was provided, go HF
    if not local_model_dir:
        logger.info("No local_model_dir provided; using HF model.")
        return hf_model_name

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

        # List everything inside (files/folders)
        children = os.listdir(local_model_dir)

        # Collect child folders that contain config.json
        candidate_folders = []
        for child in children:

            child_path = os.path.join(local_model_dir, child)

            if os.path.isdir(child_path):
                child_config = os.path.join(child_path, "config.json")
                if os.path.isfile(child_config):
                    candidate_folders.append(child_path)

        # If exactly one valid folder, use it
        if len(candidate_folders) == 1:
            chosen = candidate_folders[0]
            logger.info(
                f"Found one valid pretrained model folder inside "
                f"{local_model_dir}: {chosen}"
            )
            return chosen

        # If multiple valid folders exist, don't guess
        if len(candidate_folders) > 1:
            logger.warning(
                f"Multiple pretrained model folders found inside {local_model_dir}: "
                f"{candidate_folders}. Falling back to HF model id. "
                f"(Set LOCAL_MODEL_DIR to the exact folder you want.)"
            )
            return hf_model_name

    # ------------------------------------------------------------
    # Case 3) nothing valid locally -> fallback HF
    # ------------------------------------------------------------
    logger.info(
        f"No valid local pretrained model found in: {local_model_dir}. "
        f"Falling back to HF model: {hf_model_name}"
    )
    return hf_model_name
