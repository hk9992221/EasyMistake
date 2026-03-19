"""S3 object storage client utilities."""

from pathlib import Path
from typing import Optional
import logging

import boto3
from botocore.exceptions import ClientError

from api.core.config import settings

logger = logging.getLogger(__name__)


class S3Client:
    """Thin wrapper around boto3 S3 client."""

    def __init__(self):
        self.client = boto3.client(
            "s3",
            endpoint_url=settings.S3_ENDPOINT,
            aws_access_key_id=settings.S3_ACCESS_KEY,
            aws_secret_access_key=settings.S3_SECRET_KEY,
            region_name=settings.S3_REGION,
        )
        self.bucket = settings.S3_BUCKET

    def upload_file(
        self,
        file_path: Path,
        object_key: str,
        content_type: Optional[str] = None,
    ) -> bool:
        """Upload a local file to S3."""
        try:
            extra_args = {}
            if content_type:
                extra_args["ContentType"] = content_type

            self.client.upload_file(
                str(file_path),
                self.bucket,
                object_key,
                ExtraArgs=extra_args,
            )
            logger.info("Successfully uploaded %s to s3://%s/%s", file_path, self.bucket, object_key)
            return True
        except ClientError as exc:
            logger.error("Failed to upload %s to S3: %s", file_path, exc)
            return False

    def download_file(self, object_key: str, file_path: Path) -> bool:
        """Download a file from S3 to local path."""
        try:
            file_path.parent.mkdir(parents=True, exist_ok=True)
            self.client.download_file(self.bucket, object_key, str(file_path))
            logger.info("Successfully downloaded s3://%s/%s to %s", self.bucket, object_key, file_path)
            return True
        except ClientError as exc:
            logger.error("Failed to download %s from S3: %s", object_key, exc)
            return False

    def delete_file(self, object_key: str) -> bool:
        """Delete a file from S3."""
        try:
            self.client.delete_object(Bucket=self.bucket, Key=object_key)
            logger.info("Successfully deleted s3://%s/%s", self.bucket, object_key)
            return True
        except ClientError as exc:
            logger.error("Failed to delete %s from S3: %s", object_key, exc)
            return False

    def get_presigned_url(self, object_key: str, expiration: int = 3600) -> Optional[str]:
        """Create a presigned download URL."""
        try:
            return self.client.generate_presigned_url(
                "get_object",
                Params={"Bucket": self.bucket, "Key": object_key},
                ExpiresIn=expiration,
            )
        except ClientError as exc:
            logger.error("Failed to generate presigned URL for %s: %s", object_key, exc)
            return None

    def get_file(self, object_key: str) -> tuple[Optional[bytes], Optional[str]]:
        """Read object bytes and content type from S3."""
        try:
            response = self.client.get_object(Bucket=self.bucket, Key=object_key)
            file_content = response["Body"].read()
            content_type = response.get("ContentType", "application/octet-stream")
            logger.info("Successfully retrieved s3://%s/%s", self.bucket, object_key)
            return file_content, content_type
        except ClientError as exc:
            logger.error("Failed to get file content for %s: %s", object_key, exc)
            return None, None

    def file_exists(self, object_key: str) -> bool:
        """Check whether object exists in S3."""
        try:
            self.client.head_object(Bucket=self.bucket, Key=object_key)
            return True
        except ClientError:
            return False

    def copy_file(self, source_key: str, dest_key: str) -> bool:
        """Copy an object within the same bucket."""
        try:
            copy_source = {"Bucket": self.bucket, "Key": source_key}
            self.client.copy_object(
                CopySource=copy_source,
                Bucket=self.bucket,
                Key=dest_key,
            )
            logger.info(
                "Successfully copied s3://%s/%s to s3://%s/%s",
                self.bucket,
                source_key,
                self.bucket,
                dest_key,
            )
            return True
        except ClientError as exc:
            logger.error("Failed to copy %s to %s: %s", source_key, dest_key, exc)
            return False


s3_client = S3Client()
