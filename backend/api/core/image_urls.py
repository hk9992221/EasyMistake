from uuid import UUID

from fastapi import Request


def build_image_proxy_url(request: Request | None, image_id: UUID) -> str:
    relative_path = f"/api/v1/images/{image_id}/file"
    if request is None:
        return relative_path
    return f"{str(request.base_url).rstrip('/')}{relative_path}"
