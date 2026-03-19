from typing import Any, Optional
from fastapi import HTTPException, status
from api.core.error_codes import ErrorCode


class AppException(HTTPException):
    """Base exception for application errors"""

    def __init__(
        self,
        status_code: int,
        detail: Any = None,
        headers: Optional[dict] = None,
        code: ErrorCode = ErrorCode.INTERNAL_ERROR,
    ):
        super().__init__(status_code=status_code, detail=detail, headers=headers)
        self.code = code


class NotFoundError(AppException):
    """Resource not found"""

    def __init__(self, detail: str = "Resource not found"):
        super().__init__(status_code=status.HTTP_404_NOT_FOUND, detail=detail, code=ErrorCode.NOT_FOUND)


class BadRequestError(AppException):
    """Bad request"""

    def __init__(self, detail: str = "Bad request"):
        super().__init__(status_code=status.HTTP_400_BAD_REQUEST, detail=detail, code=ErrorCode.BAD_REQUEST)


class UnauthorizedError(AppException):
    """Unauthorized"""

    def __init__(self, detail: str = "Unauthorized"):
        super().__init__(status_code=status.HTTP_401_UNAUTHORIZED, detail=detail, code=ErrorCode.UNAUTHORIZED)


class ForbiddenError(AppException):
    """Forbidden"""

    def __init__(self, detail: str = "Forbidden"):
        super().__init__(status_code=status.HTTP_403_FORBIDDEN, detail=detail, code=ErrorCode.FORBIDDEN)


class ConflictError(AppException):
    """Conflict"""

    def __init__(self, detail: str = "Resource already exists"):
        super().__init__(status_code=status.HTTP_409_CONFLICT, detail=detail, code=ErrorCode.CONFLICT)


class ValidationError(AppException):
    """Validation error"""

    def __init__(self, detail: str = "Validation error"):
        super().__init__(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=detail, code=ErrorCode.VALIDATION_ERROR)
