"""
gcs.py

Optional helper to download a Hugging Face "save_pretrained" folder
from Google Cloud Storage (GCS) into LOCAL_MODEL_DIR.

Rules (your requirements):
- NO auth / credentials handling here.
- If env var GCS_MODEL_URI is NOT set -> do nothing (no-op).
- If it IS set -> try to download the folder.

Later on Cloud Run:
- Deployer sets permissions outside the repo.
- Container just downloads if it can.

Expected GCS structure:
gs://your-bucket/path/to/cxiu_blip_baseline/
    config.json
    pytorch_model.bin
    preprocessor_config.json
    ...

We download into:
LOCAL_MODEL_DIR (from .env / config.py)
"""

# -------------------------------
# Standard library imports
# -------------------------------

import os          # read environment variables
from pathlib import Path  # safe path handling

# -------------------------------
# Project imports
# -------------------------------

from xplain_package.config import get_settings   # central env-based config
from xplain_package.utils.logging import get_logger  # project logger helper

# Create logger for this module
logger = get_logger(__name__)


# ------------------------------------------------------------
# Lazy GCS import
# ------------------------------------------------------------
def _lazy_import_gcs_client():
    """
    Import google-cloud-storage ONLY when needed.

    Why?
    - Local dev should NOT require GCS packages.
    - If someone doesn't deploy, they don't need this dependency.

    Returns
    -------
    storage.Client class (from google.cloud)
    """
    try:
        from google.cloud import storage
        return storage.Client
    except Exception as e:
        raise ImportError(
            "google-cloud-storage is not installed. "
            "Install it ONLY when you deploy with GCS.\n"
            "pip install google-cloud-storage\n"
            f"Original error: {e}"
        )


# ------------------------------------------------------------
# Parse gs:// URI
# ------------------------------------------------------------
def parse_gs_uri(gs_uri: str):
    """
    Parse a gs://bucket/path URI into (bucket, prefix).

    Example:
        gs://my-bucket/models/cxiu_blip_baseline

    Returns
    -------
    (bucket_name, prefix)
        bucket_name = "my-bucket"
        prefix      = "models/cxiu_blip_baseline"
    """

    # Remove scheme
    no_scheme = gs_uri.replace("gs://", "")

    # Split at first slash
    parts = no_scheme.split("/", 1)

    bucket_name = parts[0]
    prefix = parts[1] if len(parts) > 1 else ""

    return bucket_name, prefix


# ------------------------------------------------------------
# Download whole folder (prefix) from GCS
# ------------------------------------------------------------
def download_gcs_folder(gs_uri: str, local_dir: str):
    """
    Download an entire "folder" from GCS into local_dir.

    Parameters
    ----------
    gs_uri : str
        URI like gs://bucket/path/to/folder
    local_dir : str
        Local target folder

    Notes
    -----
    - GCS doesn't really have folders, only object prefixes.
    - We list all objects under the prefix and download them.
    """

    # Import client lazily so local users aren't forced to install it
    StorageClient = _lazy_import_gcs_client()

    # Create a GCS client
    client = StorageClient()

    # Parse bucket + prefix
    bucket_name, prefix = parse_gs_uri(gs_uri)

    # List blobs under prefix
    blobs = client.list_blobs(bucket_name, prefix=prefix)

    # Ensure local target directory exists
    local_dir_path = Path(local_dir)
    local_dir_path.mkdir(parents=True, exist_ok=True)

    # Download each blob
    for blob in blobs:

        # Full object name in the bucket
        blob_name = blob.name

        # Compute local relative path (strip prefix)
        relative_path = blob_name[len(prefix):].lstrip("/")
        target_path = local_dir_path / relative_path

        # Ensure parent folder exists
        target_path.parent.mkdir(parents=True, exist_ok=True)

        logger.info(f"Downloading gs://{bucket_name}/{blob_name} -> {target_path}")

        # Download to disk
        blob.download_to_filename(str(target_path))


# ------------------------------------------------------------
# Main entrypoint (used by Docker)
# ------------------------------------------------------------
def main():
    """
    Main entrypoint run at container startup.

    Behavior:
    - If GCS_MODEL_URI is not set -> no-op (local mode)
    - If set -> download to LOCAL_MODEL_DIR
    """

    settings = get_settings()

    # Read optional GCS URI from env
    gs_uri = os.getenv("GCS_MODEL_URI", "").strip()

    # No URI -> local mode
    if not gs_uri:
        logger.info("GCS_MODEL_URI not set. Skipping GCS download (local mode).")
        return

    # URI provided -> download model
    logger.info(f"GCS_MODEL_URI detected: {gs_uri}")
    logger.info(f"Downloading model into LOCAL_MODEL_DIR={settings.LOCAL_MODEL_DIR}")

    download_gcs_folder(gs_uri, settings.LOCAL_MODEL_DIR)

    logger.info("GCS model download finished successfully.")


# Allow: python -m xplain_package.io.gcs
if __name__ == "__main__":
    main()
