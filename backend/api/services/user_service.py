from uuid import UUID
from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from api.models.user import User, UserRole
from api.models.invite import Invite
from api.schemas.user import UserCreate, UserUpdate, InviteCreate
from api.core.auth import get_password_hash, verify_password
from api.core.exceptions import ConflictError, NotFoundError, BadRequestError
from api.core.datetime_utils import utcnow
import secrets


class UserService:
    """Service for user-related operations"""

    async def create_user(self, db: AsyncSession, user_data: UserCreate) -> User:
        result = await db.execute(select(User).where(User.email == user_data.email))
        if result.scalar_one_or_none():
            raise ConflictError(detail="Email already registered")

        invite = None
        if user_data.invite_code:
            invite = await self._validate_invite_code(db, user_data.invite_code)

        user = User(
            email=user_data.email,
            password_hash=get_password_hash(user_data.password),
            role=UserRole.USER,
        )

        db.add(user)

        if invite:
            invite.used_count += 1

        await db.commit()
        await db.refresh(user)
        return user

    async def get_user_by_id(self, db: AsyncSession, user_id: UUID) -> User:
        result = await db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        if not user:
            raise NotFoundError(detail="User not found")
        return user

    async def get_user_by_email(self, db: AsyncSession, email: str) -> Optional[User]:
        result = await db.execute(select(User).where(User.email == email))
        return result.scalar_one_or_none()

    async def update_user(self, db: AsyncSession, user_id: UUID, user_data: UserUpdate) -> User:
        user = await self.get_user_by_id(db, user_id)

        if user_data.email is not None:
            result = await db.execute(
                select(User).where(and_(User.email == user_data.email, User.id != user_id))
            )
            if result.scalar_one_or_none():
                raise ConflictError(detail="Email already taken")
            user.email = user_data.email

        await db.commit()
        await db.refresh(user)
        return user

    async def change_password(
        self,
        db: AsyncSession,
        user_id: UUID,
        old_password: str,
        new_password: str
    ) -> User:
        user = await self.get_user_by_id(db, user_id)

        if not verify_password(old_password, user.password_hash):
            raise BadRequestError(detail="Incorrect password")

        user.password_hash = get_password_hash(new_password)
        await db.commit()
        await db.refresh(user)
        return user

    async def list_users(
        self,
        db: AsyncSession,
        skip: int = 0,
        limit: int = 100
    ) -> List[User]:
        result = await db.execute(select(User).offset(skip).limit(limit))
        return result.scalars().all()

    async def create_invite(self, db: AsyncSession, invite_data: InviteCreate, created_by: UUID) -> Invite:
        code = secrets.token_urlsafe(16)

        invite = Invite(
            code=code,
            email=invite_data.email,
            max_uses=invite_data.max_uses,
            expires_at=invite_data.expires_at,
            created_by=created_by,
        )

        db.add(invite)
        await db.commit()
        await db.refresh(invite)
        return invite

    async def list_invites(
        self,
        db: AsyncSession,
        skip: int = 0,
        limit: int = 100
    ) -> List[Invite]:
        result = await db.execute(select(Invite).offset(skip).limit(limit))
        return result.scalars().all()

    async def delete_invite(self, db: AsyncSession, invite_id: UUID) -> None:
        result = await db.execute(select(Invite).where(Invite.id == invite_id))
        invite = result.scalar_one_or_none()
        if not invite:
            raise NotFoundError(detail="Invite not found")

        await db.delete(invite)
        await db.commit()

    async def _validate_invite_code(self, db: AsyncSession, code: str) -> Optional[Invite]:
        result = await db.execute(select(Invite).where(Invite.code == code))
        invite = result.scalar_one_or_none()

        if not invite:
            raise BadRequestError(detail="Invalid invite code")

        if invite.expires_at and invite.expires_at < utcnow():
            raise BadRequestError(detail="Invite code has expired")

        if invite.used_count >= invite.max_uses:
            raise BadRequestError(detail="Invite code has been fully used")

        return invite


user_service = UserService()
