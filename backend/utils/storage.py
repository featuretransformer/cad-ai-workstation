"""
MinIO object storage utilities.
"""
from minio import Minio
from minio.error import S3Error
from config import get_settings
import os

_client = None


def get_minio_client() -> Minio:
    global _client
    if _client is None:
        s = get_settings()
        _client = Minio(
            s.minio_endpoint,
            access_key=s.minio_access_key,
            secret_key=s.minio_secret_key,
            secure=s.minio_secure,
        )
    return _client


async def init_storage():
    """Create bucket on startup if it doesn't exist."""
    try:
        s = get_settings()
        client = get_minio_client()
        if not client.bucket_exists(s.minio_bucket):
            client.make_bucket(s.minio_bucket)
    except Exception as e:
        print(f"MinIO init warning: {e} (continuing without object storage)")


def upload_file(local_path: str, object_name: str) -> str:
    """Upload a file and return the object path."""
    try:
        s = get_settings()
        client = get_minio_client()
        client.fput_object(s.minio_bucket, object_name, local_path)
        return f"{s.minio_bucket}/{object_name}"
    except Exception as e:
        print(f"Upload failed: {e}")
        return local_path  # Return local path as fallback
