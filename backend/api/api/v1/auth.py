from uuid import UUID
from datetime import timedelta, datetime, date, time
from fastapi import APIRouter, Depends, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from api.core.database import get_db
from api.core.security import create_access_token
from api.core.deps import get_current_user, require_admin
from api.services.user_service import user_service
from api.schemas.user import (
    UserCreate,
    UserResponse,
    UserUpdate,
    Token,
    ChangePassword,
    InviteCreate,
    InviteResponse,
)
from api.models.user import User
from api.models.api_call_log import ApiCallLog
from api.core.config import settings
from api.core.auth import authenticate_user
from api.core.exceptions import UnauthorizedError
from api.core.datetime_utils import utcnow
from pydantic import BaseModel, ConfigDict


router = APIRouter(prefix="/auth", tags=["Authentication"])


class _AuthBaseModel(BaseModel):
    model_config = ConfigDict(protected_namespaces=())


class UserDashboardCostResponse(_AuthBaseModel):
    start_date: datetime
    end_date: datetime
    total_calls: int
    total_tokens: int
    prompt_tokens: int
    completion_tokens: int
    total_cost_usd: float
    total_cost_cny: float
    avg_latency_ms: float | None
    calls_by_date: dict
    calls_by_purpose: dict
    calls_by_model: dict


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(
    user_data: UserCreate,
    db: AsyncSession = Depends(get_db),
):
    return await user_service.create_user(db, user_data)


@router.post("/login", response_model=Token)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db),
):
    user = await user_service.get_user_by_email(db, form_data.username)

    if not user or not authenticate_user(user, form_data.password):
        raise UnauthorizedError(detail="Incorrect email or password")

    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": str(user.id), "role": user.role.value},
        expires_delta=access_token_expires,
    )

    return Token(
        access_token=access_token,
        user=UserResponse.model_validate(user),
    )


@router.get("/me", response_model=UserResponse)
async def get_me(
    current_user: User = Depends(get_current_user),
):
    return current_user


@router.get("/me/dashboard", response_model=UserDashboardCostResponse)
async def get_my_dashboard(
    start_day: date | None = None,
    end_day: date | None = None,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if start_day:
        start_date = datetime.combine(start_day, time.min)
    if end_day:
        end_date = datetime.combine(end_day, time.max)
    if not start_date:
        start_date = utcnow() - timedelta(days=30)
    if not end_date:
        end_date = utcnow()

    base_filters = (
        ApiCallLog.user_id == current_user.id,
        ApiCallLog.created_at >= start_date,
        ApiCallLog.created_at <= end_date,
    )

    total_calls_result = await db.execute(
        select(func.count()).where(*base_filters)
    )
    total_calls = total_calls_result.scalar() or 0

    usage_rows_result = await db.execute(
        select(ApiCallLog.usage_json).where(*base_filters)
    )
    total_tokens = 0
    prompt_tokens = 0
    completion_tokens = 0
    for usage in usage_rows_result.scalars().all():
        usage_obj = usage if isinstance(usage, dict) else {}
        total_tokens += int(usage_obj.get("total_tokens", 0) or 0)
        prompt_tokens += int(usage_obj.get("prompt_tokens", 0) or 0)
        completion_tokens += int(usage_obj.get("completion_tokens", 0) or 0)

    total_cost_result = await db.execute(
        select(func.coalesce(func.sum(ApiCallLog.cost_usd), 0)).where(*base_filters)
    )
    total_cost = total_cost_result.scalar() or 0

    avg_latency_result = await db.execute(
        select(func.avg(ApiCallLog.latency_ms)).where(*base_filters)
    )
    avg_latency = avg_latency_result.scalar()

    date_stats_result = await db.execute(
        select(
            func.date(ApiCallLog.created_at).label("date"),
            func.count().label("count"),
            func.sum(ApiCallLog.cost_usd).label("cost"),
        ).where(
            *base_filters
        ).group_by(
            func.date(ApiCallLog.created_at)
        ).order_by(
            func.date(ApiCallLog.created_at)
        )
    )
    calls_by_date = {
        str(row.date): {
            "count": row.count,
            "cost": float(row.cost) if row.cost else 0,
        }
        for row in date_stats_result
    }

    purpose_stats_result = await db.execute(
        select(
            ApiCallLog.purpose,
            func.count().label("count"),
            func.sum(ApiCallLog.cost_usd).label("cost"),
        ).where(
            *base_filters
        ).group_by(ApiCallLog.purpose)
    )
    calls_by_purpose = {
        (row.purpose or "unknown"): {
            "count": row.count,
            "cost": float(row.cost) if row.cost else 0,
        }
        for row in purpose_stats_result
    }

    model_stats_result = await db.execute(
        select(
            ApiCallLog.model_name,
            func.count().label("count"),
            func.sum(ApiCallLog.cost_usd).label("cost"),
        ).where(
            *base_filters
        ).group_by(ApiCallLog.model_name)
    )
    calls_by_model = {
        (row.model_name or "unknown"): {
            "count": row.count,
            "cost": float(row.cost) if row.cost else 0,
        }
        for row in model_stats_result
    }

    return UserDashboardCostResponse(
        start_date=start_date,
        end_date=end_date,
        total_calls=total_calls,
        total_tokens=total_tokens,
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        total_cost_usd=float(total_cost),
        total_cost_cny=float(total_cost),
        avg_latency_ms=float(avg_latency) if avg_latency is not None else None,
        calls_by_date=calls_by_date,
        calls_by_purpose=calls_by_purpose,
        calls_by_model=calls_by_model,
    )


@router.post("/logout")
async def logout(
    current_user: User = Depends(get_current_user),
):
    # 对于 JWT token-based 认证，登出主要在客户端处理（清除token）
    # 后端可以添加token到黑名单等逻辑，如果需要的话
    return {"message": "Successfully logged out"}


@router.post("/change-password")
async def change_password(
    password_data: ChangePassword,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await user_service.change_password(
        db,
        current_user.id,
        password_data.old_password,
        password_data.new_password,
    )
    return {"message": "Password changed successfully"}


@router.patch("/me", response_model=UserResponse)
async def update_me(
    user_data: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await user_service.update_user(db, current_user.id, user_data)


@router.post("/invites", response_model=InviteResponse, status_code=status.HTTP_201_CREATED)
async def create_invite(
    invite_data: InviteCreate,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    return await user_service.create_invite(db, invite_data, current_user.id)


@router.get("/invites", response_model=list[InviteResponse])
async def list_invites(
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    return await user_service.list_invites(db, skip, limit)


@router.delete("/invites/{invite_id}")
async def delete_invite(
    invite_id: UUID,
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    await user_service.delete_invite(db, invite_id)
    return {"message": "Invite deleted successfully"}
