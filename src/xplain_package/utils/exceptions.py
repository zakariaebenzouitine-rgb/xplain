class ModelLoadError(RuntimeError):
    """Raised when a model cannot be loaded."""
    pass

class InvalidInputError(ValueError):
    """Raised when user input is invalid (missing file, bad type, etc.)."""
    pass
