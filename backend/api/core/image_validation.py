import hashlib
import io
import warnings

from PIL import Image, UnidentifiedImageError

from api.core.config import settings
from api.core.exceptions import BadRequestError


FORMATS = {"JPEG": ("image/jpeg", ".jpg"), "PNG": ("image/png", ".png"),
           "WEBP": ("image/webp", ".webp"), "GIF": ("image/gif", ".gif")}


def inspect_image(data: bytes) -> dict:
    if not data:
        raise BadRequestError(detail="图片不能为空")
    if len(data) > settings.IMAGE_MAX_UPLOAD_BYTES:
        raise BadRequestError(detail=f"图片不能超过 {settings.IMAGE_MAX_UPLOAD_BYTES // (1024 * 1024)} MB")
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(io.BytesIO(data), formats=list(FORMATS)) as image:
                width, height = image.size
                if width * height > settings.IMAGE_MAX_PIXELS:
                    raise BadRequestError(detail="图片像素过多，请缩小后上传")
                if getattr(image, "is_animated", False):
                    raise BadRequestError(detail="请上传静态图片")
                mime, extension = FORMATS[image.format]
                image.verify()
            # verify() alone does not decode JPEG pixels or catch every truncation.
            with Image.open(io.BytesIO(data), formats=list(FORMATS)) as image:
                image.load()
    except (UnidentifiedImageError, OSError, SyntaxError, ValueError,
            Image.DecompressionBombError, Image.DecompressionBombWarning) as exc:
        raise BadRequestError(detail="图片损坏或格式不支持，请使用 PNG、JPEG、WebP 或静态 GIF") from exc
    return {"mime": mime, "extension": extension, "width": width, "height": height,
            "size_bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}
