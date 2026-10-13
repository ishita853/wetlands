"""S3-compatible object storage client.

Backs future storage of GeoTIFF, NetCDF, CSV, GeoJSON, and Shapefile ZIP
datasets. Configured entirely from environment variables; no upload/download
logic is implemented yet.
"""

from functools import cached_property

import boto3

from app.core.config import settings


class StorageClient:
    def __init__(self) -> None:
        self.bucket = settings.S3_BUCKET or None

    def is_configured(self) -> bool:
        return bool(self.bucket and settings.S3_ENDPOINT)

    @cached_property
    def client(self):
        return boto3.client(
            "s3",
            endpoint_url=settings.S3_ENDPOINT or None,
            aws_access_key_id=settings.S3_ACCESS_KEY or None,
            aws_secret_access_key=settings.S3_SECRET_KEY or None,
            region_name=settings.S3_REGION or None,
        )
