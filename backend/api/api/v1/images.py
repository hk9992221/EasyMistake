from uuid import UUID

from fastapi import APIRouter, Depends, File, UploadFile, status, Query
from fastapi.responses import Response
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from api.core.database import get_db
from api.core.deps import get_current_user
from api.core.security import decode_access_token
from api.models.user import User, UserRole
from api.models.image import Image
from api.schemas.image import (
    ImageCreate,
    ImageResponse,
    UploadUrlResponse,
    ImageUploadUrlRequest,
)
from api.services.image_service import image_service
from api.core.exceptions import NotFoundError, ForbiddenError, UnauthorizedError


router = APIRouter(prefix="/images", tags=["Images"])
optional_security = HTTPBearer(auto_error=False)


async def get_current_user_from_header_or_query(
    credentials: HTTPAuthorizationCredentials | None = Depends(optional_security),
    token: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
) -> User:
    bearer_token = credentials.credentials if credentials else None
    raw_token = bearer_token or token
    if not raw_token:
        raise UnauthorizedError(detail="Not authenticated")

    payload = decode_access_token(raw_token)
    user_id_str = payload.get("sub")
    if not user_id_str:
        raise UnauthorizedError(detail="Invalid token")

    try:
        user_id = UUID(user_id_str)
    except ValueError:
        raise UnauthorizedError(detail="Invalid token")

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user is None:
        raise UnauthorizedError(detail="User not found")
    if not user.is_active:
        raise UnauthorizedError(detail="User is inactive")
    return user


@router.post("/upload-url", response_model=UploadUrlResponse)
async def create_upload_url(
    payload: ImageUploadUrlRequest,
    current_user: User = Depends(get_current_user),
):
    upload_url, object_key = image_service.generate_upload_url(
        current_user.id,
        payload.filename,
        payload.content_type,
    )
    return UploadUrlResponse(upload_url=upload_url, object_key=object_key)


@router.post("", response_model=ImageResponse, status_code=status.HTTP_201_CREATED)
@router.post("/", response_model=ImageResponse, status_code=status.HTTP_201_CREATED, include_in_schema=False)
async def create_image(
    image_data: ImageCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await image_service.create_image_record(db, current_user.id, image_data)


@router.post("/upload", response_model=ImageResponse, status_code=status.HTTP_201_CREATED)
async def upload_image(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    file_bytes = await file.read()
    return await image_service.create_image_from_upload(
        db,
        current_user.id,
        file.filename or "upload",
        file.content_type,
        file_bytes,
    )


@router.get("", response_model=list[ImageResponse])
@router.get("/", response_model=list[ImageResponse], include_in_schema=False)
async def list_images(
    skip: int = 0,
    limit: int = 50,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    is_admin = current_user.role == UserRole.ADMIN
    return await image_service.list_images(db, current_user.id, is_admin=is_admin, skip=skip, limit=limit)


@router.get("/{image_id}", response_model=ImageResponse)
async def get_image(
    image_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    is_admin = current_user.role == UserRole.ADMIN
    return await image_service.get_image_or_404(db, image_id, current_user.id, is_admin=is_admin)


@router.delete("/{image_id}")
async def delete_image(
    image_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    is_admin = current_user.role == UserRole.ADMIN
    await image_service.delete_image(db, image_id, current_user.id, is_admin=is_admin)
    return {"message": "Image deleted successfully"}


@router.get("/{image_id}/file", response_class=Response)
async def get_image_file(
    image_id: UUID,
    current_user: User = Depends(get_current_user_from_header_or_query),
    db: AsyncSession = Depends(get_db),
):
    """
    Get image file by ID (proxy endpoint to S3/MinIO)

    This endpoint acts as a proxy to the object storage, handling:
    - Authentication
    - Authorization
    - CORS
    - Streaming
    - Caching
    """
    # Get image record
    result = await db.execute(select(Image).where(Image.id == image_id))
    image = result.scalar_one_or_none()

    if not image:
        raise NotFoundError(detail="Image not found")

    # Check permission
    is_admin = current_user.role == UserRole.ADMIN
    if not is_admin and image.user_id != current_user.id:
        raise ForbiddenError(detail="You don't have permission to access this image")

    # Fetch image bytes from S3
    try:
        image_bytes = image_service.fetch_image_bytes(image.object_key)
    except Exception as e:
        raise NotFoundError(detail=f"Failed to fetch image from storage: {str(e)}")

    # Return image with proper content type and cache headers
    return Response(
        content=image_bytes,
        media_type=image.mime or "image/jpeg",
        headers={
            "Cache-Control": "public, max-age=31536000, immutable",
            "Content-Disposition": f'inline; filename="{image.object_key.split("/")[-1]}"',
        },
    )
