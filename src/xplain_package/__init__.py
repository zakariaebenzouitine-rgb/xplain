"""
xplain_package/__init__.py

This is the public entrypoint of the package.

Anything we import here becomes easy to access like:

    from xplain_package import predict_caption

We keep this file small and stable so coworkers know where to look
for the "main functions" of the project.
"""

# Import the two public inference helpers
# - predict_caption: generate a caption from one image path
# - load_captioner: loads & caches the BLIP model once (useful for FastAPI startup)
from xplain_package.inference.predict import predict_caption, load_captioner

# Define what should be considered "public" in this package
__all__ = [
    "predict_caption",
    "load_captioner",
]
