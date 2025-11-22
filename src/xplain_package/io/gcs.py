"""
xplain_package/io/gcs.py

Downloads a finetuned model from GCS into LOCAL_MODEL_DIR.

Rules:
- If GCS_MODEL_URI empty -> no-op
- If bucket is private -> ADC MUST be available, otherwise fail clearly
- Anonymous mode is allowed only if ALLOW_PUBLIC_GCS=true
"""

import os
import sys
import shutil
import logging
from pathlib import Path
from urllib.parse import urlparse

from google.cloud import storage
from google.auth.exceptions import DefaultCredentialsError

from xplain_package.config import settings


logger = logging.getLogger("xplain_package.io.gcs")
logging.basicConfig(level=getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO))


def parse_gs_uri(gs_uri: str):
    if not gs_uri.startswith("gs://"):
        raise ValueError(f"Invalid GCS URI (must start with gs://): {gs_uri}")
    parsed = urlparse(gs_uri)
    bucket = parsed.netloc
    prefix = parsed.path.lstrip("/")
    return bucket, prefix


def _get_project_id():
    return (
        os.getenv("GOOGLE_CLOUD_PROJECT")
        or os.getenv("GCP_PROJECT")
        or os.getenv("GCLOUD_PROJECT")
        or os.getenv("PROJECT_ID")
    )


def _make_client():
    """
    Create GCS client.

    Priority:
    1) Authenticated client using ADC (private buckets)
    2) Anonymous client ONLY if ALLOW_PUBLIC_GCS=true
    """
    project_id = _get_project_id()
    allow_public = os.getenv("ALLOW_PUBLIC_GCS", "false").lower() == "true"

    try:
        if project_id:
            logger.info(f"Creating authenticated GCS client with project={project_id}")
            return storage.Client(project=project_id)
        logger.info("Creating authenticated GCS client (project inferred from ADC).")
        return storage.Client()

    except (DefaultCredentialsError, OSError) as e:
        if allow_public:
            logger.warning(
                f"ADC not found ({e}). Using anonymous client because ALLOW_PUBLIC_GCS=true."
            )
            return storage.Client.create_anonymous_client()

        raise DefaultCredentialsError(
            "ADC credentials not found inside container, and ALLOW_PUBLIC_GCS is false.\n"
            "For private buckets, mount ADC json and set GOOGLE_APPLICATION_CREDENTIALS.\n"
            "Example:\n"
            "  -v ~/.config/gcloud/application_default_credentials.json:/tmp/adc.json:ro\n"
            "  -e GOOGLE_APPLICATION_CREDENTIALS=/tmp/adc.json\n"
        )


def download_prefix(bucket_name: str, prefix: str, dest_dir: Path):
    client = _make_client()
    bucket = client.bucket(bucket_name)

    blobs = list(client.list_blobs(bucket, prefix=prefix))
    if not blobs:
        raise FileNotFoundError(f"No objects found at gs://{bucket_name}/{prefix}")

    dest_dir.mkdir(parents=True, exist_ok=True)

    for blob in blobs:
        rel = blob.name[len(prefix):].lstrip("/") if blob.name != prefix else Path(blob.name).name
        target = dest_dir / rel
        target.parent.mkdir(parents=True, exist_ok=True)

        logger.info(f"Downloading gs://{bucket_name}/{blob.name} -> {target}")
        blob.download_to_filename(str(target))


def main():
    gs_uri = settings.GCS_MODEL_URI
    local_model_dir = Path(settings.LOCAL_MODEL_DIR).resolve()

    logger.info(f"GCS_MODEL_URI = {gs_uri}")
    logger.info(f"LOCAL_MODEL_DIR = {local_model_dir}")

    if not gs_uri:
        logger.info("No GCS_MODEL_URI set. Skipping download.")
        return 0

    bucket_name, prefix = parse_gs_uri(gs_uri)

    if local_model_dir.exists():
        logger.info(f"Cleaning existing local model dir: {local_model_dir}")
        shutil.rmtree(local_model_dir)

    try:
        download_prefix(bucket_name, prefix, local_model_dir)
        logger.info("GCS download complete.")
        return 0
    except Exception as e:
        logger.exception(f"GCS download failed: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
