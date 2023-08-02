from __future__ import annotations

import logging
import uuid
from datetime import datetime, timedelta
from functools import cache
from pathlib import PosixPath
from urllib.parse import urlparse

import aioboto3
import httpx

from hyacinth.settings import get_settings

settings = get_settings()
_logger = logging.getLogger(__name__)


@cache
def get_aws_session() -> aioboto3.Session:
    return aioboto3.Session(
        aws_access_key_id=settings.s3_access_key, aws_secret_access_key=settings.s3_secret_key
    )


async def mirror_image(url: str) -> str:
    """
    Mirror an image to s3.

    Args:
        url: the url of the image to mirror

    Returns:
        the url of the image mirror
    """
    if settings.s3_bucket is None:
        raise ValueError("setting.s3_bucket must be set!")

    async with httpx.AsyncClient() as client:
        image_response = await client.get(url)
    image_response.raise_for_status()

    image_key = str(uuid.uuid4())
    file_extension = PosixPath(urlparse(url).path).suffix
    if file_extension:
        image_key = f"{image_key}{file_extension}"

    expiration_time = datetime.now() + timedelta(days=settings.s3_image_mirror_expiration_days)

    _logger.debug(f"Mirroring image {url} to s3 {settings.s3_url}/{settings.s3_bucket}/{image_key}")

    session = get_aws_session()
    async with session.client("s3", endpoint_url=settings.s3_url) as s3:
        await s3.put_object(
            Bucket=settings.s3_bucket,
            Key=image_key,
            Body=image_response.content,
            Expires=expiration_time,
        )

    return f"{settings.s3_url}/{settings.s3_bucket}/{image_key}"
