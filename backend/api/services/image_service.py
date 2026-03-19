import hashlib
import os
import re
from typing import Optional, Tuple
from uuid import UUID, uuid4

import boto3
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.core.config import settings
from api.core.exceptions import BadRequestError, ForbiddenError, NotFoundError
from api.models.image import Image
from api.schemas.image import ImageCreate, ImageUpdate
from api.services.base import BaseService


class ImageService(BaseService[Image, ImageCreate, ImageUpdate]):
    def __init__(self) -> None:
        super().__init__(Image)
        self._s3_client = None

    def _get_s3_client(self):
        if self._s3_client is None:
            self._s3_client = boto3.client(
                "s3",
                endpoint_url=settings.S3_ENDPOINT,
                aws_access_key_id=settings.S3_ACCESS_KEY,
                aws_secret_access_key=settings.S3_SECRET_KEY,
                region_name=settings.S3_REGION,
            )
        return self._s3_client

    def _safe_filename(self, filename: str) -> str:
        base = os.path.basename(filename or "")
        safe = re.sub(r"[^A-Za-z0-9_.-]", "_", base)
        return safe or "upload"

    def _build_object_key(self, user_id: UUID, filename: str) -> str:
        safe_name = self._safe_filename(filename)
        return f"images/{user_id}/{uuid4().hex}_{safe_name}"

    def _build_storage_url(self, object_key: str) -> str:
        endpoint = settings.S3_ENDPOINT.rstrip("/")
        return f"{endpoint}/{settings.S3_BUCKET}/{object_key}"

    def generate_upload_url(
        self,
        user_id: UUID,
        filename: str,
        content_type: str,
        expires_in: int = 900,
    ) -> Tuple[str, str]:
        if not content_type:
            raise BadRequestError(detail="content_type is required")

        object_key = self._build_object_key(user_id, filename)
        s3_client = self._get_s3_client()
        upload_url = s3_client.generate_presigned_url(
            "put_object",
            Params={
                "Bucket": settings.S3_BUCKET,
                "Key": object_key,
                "ContentType": content_type,
            },
            ExpiresIn=expires_in,
        )
        return upload_url, object_key

    async def create_image_record(
        self,
        db: AsyncSession,
        user_id: UUID,
        image_data: ImageCreate,
    ) -> Image:
        image = Image(user_id=user_id, **image_data.model_dump())
        db.add(image)
        await db.commit()
        await db.refresh(image)
        return image

    async def create_image_from_upload(
        self,
        db: AsyncSession,
        user_id: UUID,
        filename: str,
        content_type: Optional[str],
        file_bytes: bytes,
    ) -> Image:
        if not file_bytes:
            raise BadRequestError(detail="Empty file upload")
        if not content_type or not content_type.startswith("image/"):
            raise BadRequestError(detail="Unsupported file type")

        sha256 = hashlib.sha256(file_bytes).hexdigest()
        size_bytes = len(file_bytes)
        object_key = self._build_object_key(user_id, filename)

        s3_client = self._get_s3_client()
        s3_client.put_object(
            Bucket=settings.S3_BUCKET,
            Key=object_key,
            Body=file_bytes,
            ContentType=content_type,
        )

        image = Image(
            user_id=user_id,
            object_key=object_key,
            storage_url=self._build_storage_url(object_key),
            sha256=sha256,
            mime=content_type,
            size_bytes=size_bytes,
            width=None,
            height=None,
        )
        db.add(image)
        await db.commit()
        await db.refresh(image)
        return image

    async def list_images(
        self,
        db: AsyncSession,
        user_id: UUID,
        is_admin: bool = False,
        skip: int = 0,
        limit: int = 50,
    ) -> list[Image]:
        query = select(Image).order_by(Image.created_at.desc())
        if not is_admin:
            query = query.where(Image.user_id == user_id)
        result = await db.execute(query.offset(skip).limit(limit))
        return list(result.scalars().all())

    async def get_image_or_404(
        self,
        db: AsyncSession,
        image_id: UUID,
        user_id: UUID,
        is_admin: bool = False,
    ) -> Image:
        result = await db.execute(select(Image).where(Image.id == image_id))
        image = result.scalar_one_or_none()
        if not image:
            raise NotFoundError(detail="Image not found")
        if not is_admin and image.user_id != user_id:
            raise ForbiddenError(detail="You don't have permission to access this image")
        return image

    async def delete_image(
        self,
        db: AsyncSession,
        image_id: UUID,
        user_id: UUID,
        is_admin: bool = False,
    ) -> None:
        image = await self.get_image_or_404(db, image_id, user_id, is_admin=is_admin)
        s3_client = self._get_s3_client()
        s3_client.delete_object(Bucket=settings.S3_BUCKET, Key=image.object_key)
        await db.delete(image)
        await db.commit()

    def fetch_image_bytes(self, object_key: str) -> bytes:
        s3_client = self._get_s3_client()
        response = s3_client.get_object(Bucket=settings.S3_BUCKET, Key=object_key)
        return response["Body"].read()


image_service = ImageService()
