import asyncio
import os
import re
from typing import Optional, Tuple
from uuid import UUID, uuid4

import boto3
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from botocore.exceptions import ClientError

from api.core.config import settings
from api.core.exceptions import BadRequestError, ConflictError, ForbiddenError, NotFoundError
from api.core.image_validation import FORMATS, inspect_image
from api.core.jobs import create_job
from api.models.image import Image
from api.models.question_image import QuestionImage
from api.models.answer_image import AnswerImage
from api.models.extraction_image import ExtractionImage
from api.models.job import JobType
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
        size_bytes: int,
        expires_in: int = 900,
    ) -> Tuple[str, str]:
        if content_type not in {value[0] for value in FORMATS.values()}:
            raise BadRequestError(detail="请使用 PNG、JPEG、WebP 或静态 GIF")
        if not 0 < size_bytes <= settings.IMAGE_MAX_UPLOAD_BYTES:
            raise BadRequestError(detail="上传图片超过大小限制")

        # Staging keys may be overwritten by the signed PUT until it expires.
        # Registration validates and copies bytes to a fresh, private image key.
        object_key = f"uploads/{user_id}/{uuid4().hex}_{self._safe_filename(filename)}"
        s3_client = self._get_s3_client()
        upload_url = s3_client.generate_presigned_url(
            "put_object",
            Params={
                "Bucket": settings.S3_BUCKET,
                "Key": object_key,
                "ContentType": content_type,
                "ContentLength": size_bytes,
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
        pattern = rf"uploads/{re.escape(str(user_id))}/[a-f0-9]{{32}}_[A-Za-z0-9_.-]+"
        if not re.fullmatch(pattern, image_data.object_key):
            raise ForbiddenError(detail="只能登记当前账号上传的临时图片")
        data = await asyncio.to_thread(self._read_upload_bytes, image_data.object_key)
        return await self._save_verified_image(db, user_id, data, staging_key=image_data.object_key)

    def _read_upload_bytes(self, object_key: str) -> bytes:
        try:
            response = self._get_s3_client().get_object(Bucket=settings.S3_BUCKET, Key=object_key)
        except ClientError as exc:
            raise NotFoundError(detail="上传文件不存在或暂时无法读取，请重新上传") from exc
        body = response["Body"]
        try:
            if response.get("ContentLength", 0) > settings.IMAGE_MAX_UPLOAD_BYTES:
                raise BadRequestError(detail="上传图片超过大小限制")
            return body.read(settings.IMAGE_MAX_UPLOAD_BYTES + 1)
        finally:
            body.close()

    async def create_image_from_upload(
        self,
        db: AsyncSession,
        user_id: UUID,
        filename: str,
        content_type: Optional[str],
        file_bytes: bytes,
    ) -> Image:
        return await self._save_verified_image(db, user_id, file_bytes)

    async def _save_verified_image(self, db, user_id, file_bytes, staging_key=None) -> Image:
        metadata = await asyncio.to_thread(inspect_image, file_bytes)
        object_key = self._build_object_key(user_id, "image" + metadata.pop("extension"))
        await asyncio.to_thread(self._get_s3_client().put_object,
            Bucket=settings.S3_BUCKET,
            Key=object_key,
            Body=file_bytes,
            ContentType=metadata["mime"],
        )

        image = Image(
            user_id=user_id,
            object_key=object_key,
            storage_url=self._build_storage_url(object_key),
            **metadata,
        )
        db.add(image)
        if staging_key:
            await create_job(db, user_id, JobType.IMAGE_CLEANUP, {"object_key": staging_key}, commit=False)
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
        image = (await db.execute(select(Image).where(Image.id == image_id).with_for_update()
                                 .execution_options(populate_existing=True))).scalar_one_or_none()
        if image is None:
            raise NotFoundError(detail="Image not found")
        if not is_admin and image.user_id != user_id:
            raise ForbiddenError(detail="You don't have permission to access this image")
        for link in (QuestionImage, AnswerImage, ExtractionImage):
            if await db.scalar(select(link.image_id).where(link.image_id == image_id).limit(1)):
                raise ConflictError(detail="图片仍被题目、答案或识别记录使用，请先解除关联")
        object_key, owner_id = image.object_key, image.user_id
        try:
            await db.delete(image)
            await db.flush()
            # The row deletion and cleanup task either both commit or both roll back.
            await create_job(db, owner_id, JobType.IMAGE_CLEANUP, {"object_key": object_key}, commit=False)
            await db.commit()
        except IntegrityError as exc:
            await db.rollback()
            raise ConflictError(detail="图片仍被使用，无法删除") from exc

    def delete_image_bytes(self, object_key: str) -> None:
        self._get_s3_client().delete_object(Bucket=settings.S3_BUCKET, Key=object_key)

    def fetch_image_bytes(self, object_key: str) -> bytes:
        s3_client = self._get_s3_client()
        response = s3_client.get_object(Bucket=settings.S3_BUCKET, Key=object_key)
        return response["Body"].read()


image_service = ImageService()
