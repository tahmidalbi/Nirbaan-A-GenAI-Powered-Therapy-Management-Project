from __future__ import annotations

import mimetypes
from uuid import uuid4

import boto3
from botocore.client import Config

from .config import settings


def _get_s3_client():
    if not settings.has_r2_config:
        raise ValueError("R2 configuration is incomplete")

    return boto3.client(
        "s3",
        endpoint_url=settings.R2_ENDPOINT_URL,
        aws_access_key_id=settings.R2_ACCESS_KEY_ID,
        aws_secret_access_key=settings.R2_SECRET_ACCESS_KEY,
        config=Config(signature_version="s3v4"),
        region_name="auto",
    )


def build_audio_object_key(
    *,
    patient_id: int,
    run_id: int,
    extension: str = ".wav",
) -> str:
    return f"imaginal_audio/patient_{patient_id}/run_{run_id}/{uuid4().hex}{extension}"


def upload_file_to_r2(
    *,
    local_path: str,
    object_key: str,
    content_type: str | None = None,
) -> dict:
    client = _get_s3_client()

    guessed_type, _ = mimetypes.guess_type(local_path)
    content_type = content_type or guessed_type or "application/octet-stream"

    with open(local_path, "rb") as f:
        client.upload_fileobj(
            Fileobj=f,
            Bucket=settings.R2_BUCKET_NAME,
            Key=object_key,
            ExtraArgs={"ContentType": content_type},
        )

    return {
        "object_key": object_key,
        "url": build_r2_public_url(object_key),
    }


def build_r2_public_url(object_key: str) -> str:
    base = settings.R2_ENDPOINT_URL.rstrip("/")
    bucket = settings.R2_BUCKET_NAME
    return f"{base}/{bucket}/{object_key}"


def generate_presigned_download_url(object_key: str) -> str:
    client = _get_s3_client()
    return client.generate_presigned_url(
        "get_object",
        Params={"Bucket": settings.R2_BUCKET_NAME, "Key": object_key},
        ExpiresIn=settings.R2_PRESIGNED_URL_EXPIRY,
    )