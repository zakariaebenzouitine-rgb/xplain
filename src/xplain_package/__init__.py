"""
xplain_package/__init__.py

Public entrypoint of the package.

Coworkers / API can import:
    from xplain_package import predict_caption, predict_captions
"""

# Import public inference helpers
from xplain_package.inference.predict import (
    predict_caption,
    predict_captions,
    load_captioner,
)

# Declare public API
__all__ = [
    "predict_caption",
    "predict_captions",
    "load_captioner",
]
