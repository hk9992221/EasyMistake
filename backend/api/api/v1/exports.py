from uuid import UUID
from datetime import datetime, timedelta
from pathlib import Path
from fastapi import APIRouter, Depends, status
from fastapi.responses import FileResponse, RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from api.core.database import get_db
from api.core.deps import get_current_user
from api.schemas.export import ExportCreate, ExportResponse, DownloadUrlResponse
from api.services.export_service import export_service
from api.models.user import User, UserRole
from api.models.export import Export
from api.core.exceptions import BadRequestError, ForbiddenError, NotFoundError
from api.core.config import settings
from api.core.datetime_utils import utcnow
from api.core.s3 import s3_client


router = APIRouter(prefix="/exports", tags=["Exports"])


@router.post("", response_model=ExportResponse, status_code=status.HTTP_201_CREATED)
@router.post("/", response_model=ExportResponse, status_code=status.HTTP_201_CREATED, include_in_schema=False)
async def create_export(
    export_data: ExportCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """创建新的导出任务"""
    is_admin = current_user.role == UserRole.ADMIN
    return await export_service.create_export(db, current_user.id, export_data, is_admin=is_admin)


@router.get("/paper-sets/{paper_set_id:path}", response_model=list[ExportResponse])
async def list_paper_set_exports(
    paper_set_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取特定组卷的导出历史"""
    # Validate UUID manually
    try:
        paper_set_id_uuid = UUID(paper_set_id)
    except ValueError:
        raise NotFoundError(detail="Invalid paper set ID format")

    is_admin = current_user.role == UserRole.ADMIN
    return await export_service.list_exports_by_paper_set(
        db,
        paper_set_id_uuid,
        current_user.id,
        is_admin=is_admin
    )


@router.get("", response_model=list[ExportResponse])
@router.get("/", response_model=list[ExportResponse], include_in_schema=False)
async def list_exports(
    skip: int = 0,
    limit: int = 50,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取当前用户的所有导出记录"""
    is_admin = current_user.role == UserRole.ADMIN
    return await export_service.list_exports(db, current_user.id, is_admin=is_admin, skip=skip, limit=limit)


@router.get("/{export_id}", response_model=ExportResponse)
async def get_export(
    export_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取单个导出记录详情"""
    is_admin = current_user.role == UserRole.ADMIN
    export = await export_service.get_export_by_id(db, export_id)
    if not export:
        raise NotFoundError(detail="Export not found")

    if not is_admin and export.user_id != current_user.id:
        raise ForbiddenError(detail="You don't have permission to access this export")

    return export


@router.delete("/{export_id}")
async def delete_export(
    export_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    is_admin = current_user.role == UserRole.ADMIN
    await export_service.delete_export(db, export_id, current_user.id, is_admin=is_admin)
    return {"message": "Export deleted successfully"}


@router.post("/{export_id}/download-url", response_model=DownloadUrlResponse)
async def get_export_download_url(
    export_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """获取导出文件的下载链接（预签名URL）"""
    export = await export_service.get_export_by_id(db, export_id)
    if not export:
        raise NotFoundError(detail="Export not found")

    if current_user.role != UserRole.ADMIN and export.user_id != current_user.id:
        raise ForbiddenError(detail="You don't have permission to access this export")

    if not export.object_key:
        raise BadRequestError(detail="Export is not ready")

    # 生成预签名下载URL（10分钟有效期）
    expires_at = utcnow() + timedelta(minutes=10)
    download_url = f"/exports/{export_id}/download"

    return DownloadUrlResponse(download_url=download_url, expires_at=expires_at)


@router.get("/{export_id}/download")
async def download_export(
    export_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """下载导出文件 - 直接返回文件内容"""
    # Get export record
    result = await db.execute(select(Export).where(Export.id == export_id))
    export = result.scalar_one_or_none()

    if not export:
        raise NotFoundError(detail="Export not found")

    if current_user.role != UserRole.ADMIN and export.user_id != current_user.id:
        raise ForbiddenError(detail="You don't have permission to access this export")

    if export.status != "DONE" or not export.object_key:
        raise BadRequestError(detail="Export is not ready")

    # Get file content from S3
    file_content, content_type = s3_client.get_file(export.object_key)

    if not file_content:
        raise NotFoundError(detail="Failed to download file from storage")

    # Determine filename
    filename = export.object_key.split('/')[-1]

    # Properly encode filename for Content-Disposition header
    from urllib.parse import quote
    encoded_filename = quote(filename)

    from fastapi.responses import Response
    return Response(
        content=file_content,
        media_type=content_type or "application/zip",
        headers={
            "Content-Disposition": f"attachment; filename*=UTF-8''{encoded_filename}"
        }
    )
