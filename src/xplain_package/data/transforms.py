"""
transforms.py

Inference-only image utilities.

For the BLIP baseline, we do not need manual normalization here because:
- AutoProcessor handles resizing + normalization internally.

So this file is intentionally simple:
- load_image(path) -> returns a clean RGB PIL image

Later, if a new model needs custom preprocessing,
this is the first place to update.
"""

# PIL (Python Imaging Library) is the standard way to handle images
from PIL import Image

# Our own exception type for cleaner errors upstream
from xplain_package.utils.exceptions import InvalidInputError


def load_image(image_path: str) -> Image.Image:
    """
    Load an image from disk and return a PIL Image in RGB mode.

    Parameters
    ----------
    image_path : str
        Path to an image file (png/jpg/etc).

    Returns
    -------
    PIL.Image.Image
        The loaded image in RGB format.

    Raises
    ------
    InvalidInputError
        If the path is empty or the file cannot be opened.
    """

    # Safety check: empty path is always invalid
    if not image_path:
        raise InvalidInputError("image_path is empty. Please provide a valid file path.")

    try:
        # Open image file
        img = Image.open(image_path)

        # Convert to RGB just to be safe.
        # Even if X-rays are grayscale, BLIP expects 3 channels,
        # and AutoProcessor handles that fine.
        img = img.convert("RGB")

        # Return PIL image object
        return img

    except Exception as e:
        # Wrap any PIL error into a clearer project-level error
        raise InvalidInputError(
            f"Could not open image at path: {image_path}. Error: {e}"
        )
