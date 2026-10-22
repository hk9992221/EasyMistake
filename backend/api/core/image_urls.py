from uuid import UUID

from fastapi import Request


def build_image_proxy_url(request: Request | None, image_id: UUID) -> str:
    relative_path = f"/api/v1/images/{image_id}/file"
    if request is None:
        return relative_path
    url = f"{str(request.base_url).rstrip('/')}{relative_path}"
    auth_header = request.headers.get("authorization", "")
    if auth_header.lower().startswith("bearer "):
        token = auth_header.split(" ", 1)[1].strip()
        if token:
            return f"{url}?token={token}"
    return url
