from uuid import UUID
from fastapi import Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from api.core.database import get_db
from api.core.security import decode_access_token
from api.models.user import User, UserRole
from api.core.exceptions import ForbiddenError, UnauthorizedError


security = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> User:
    """Get current authenticated user from JWT token"""
    token = credentials.credentials
    payload = decode_access_token(token)

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


async def get_current_active_user(
    current_user: User = Depends(get_current_user),
) -> User:
    """Get current active user"""
    if not current_user.is_active:
        raise UnauthorizedError(detail="User is inactive")
    return current_user


async def require_admin(
    current_user: User = Depends(get_current_user),
) -> User:
    """Require admin role"""
    if current_user.role != UserRole.ADMIN:
        raise ForbiddenError(detail="Admin access required")
    return current_user


class PermissionChecker:
    """Check if user has permission to access a resource"""

    def __init__(self, admin_only: bool = False):
        self.admin_only = admin_only

    def __call__(
        self,
        current_user: User = Depends(get_current_user),
    ) -> User:
        """Check permissions"""
        if self.admin_only and current_user.role != UserRole.ADMIN:
            raise ForbiddenError(detail="Admin access required")
        return current_user


def check_ownership_or_admin(
    resource_user_id: UUID,
    current_user: User,
) -> bool:
    """Check if user owns the resource or is admin"""
    if current_user.role == UserRole.ADMIN:
        return True
    if current_user.id == resource_user_id:
        return True
    return False


async def require_ownership_or_admin(
    resource_user_id: UUID,
    current_user: User = Depends(get_current_user),
) -> User:
    """Require user to own the resource or be admin"""
    if not check_ownership_or_admin(resource_user_id, current_user):
        raise ForbiddenError(detail="You don't have permission to access this resource")
    return current_user
