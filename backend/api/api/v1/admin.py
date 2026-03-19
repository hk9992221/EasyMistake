"""
管理员 API 路由
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, cast, String, desc, and_, or_, false
from typing import Callable, List, Optional
from datetime import datetime, timedelta, date, time
from uuid import UUID

from api.core.database import get_db
from api.core.deps import get_current_user
from api.core.auth import get_password_hash
from api.core.datetime_utils import utcnow
from api.models.user import User, UserRole
from api.models.question import Question
from api.models.paper_set import PaperSet
from api.models.api_call_log import ApiCallLog
from api.schemas.user import UserResponse, UserCreate
from api.schemas.question import QuestionResponse
from api.schemas.paper_set import PaperSetResponse
from pydantic import BaseModel, ConfigDict, EmailStr, Field


router = APIRouter(prefix="/admin", tags=["admin"])


def _parse_expression(value: str) -> List[List[str]]:
    tokens = [token for token in value.split() if token]
    groups: List[List[str]] = []
    current_group: List[str] = []

    for token in tokens:
        upper_token = token.upper()
        if upper_token == "OR":
            if current_group:
                groups.append(current_group)
                current_group = []
            continue
        if upper_token == "AND":
            continue
        current_group.append(token)

    if current_group:
        groups.append(current_group)
    return groups


def _build_expression_condition(expression: str, token_to_condition: Callable[[str], object]):
    groups = _parse_expression(expression)
    if not groups:
        return None

    or_conditions = []
    for group in groups:
        group_conditions = [token_to_condition(token) for token in group]
        if group_conditions:
            or_conditions.append(and_(*group_conditions))

    if not or_conditions:
        return None
    if len(or_conditions) == 1:
        return or_conditions[0]
    return or_(*or_conditions)


class _ApiBaseModel(BaseModel):
    model_config = ConfigDict(protected_namespaces=())


# ==================== 依赖项 ====================

async def get_current_admin(
    current_user: User = Depends(get_current_user)
) -> User:
    """获取当前管理员用户"""
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=403,
            detail="需要管理员权限"
        )
    return current_user


# ==================== Schema 定义 ====================

class AdminUserCreate(_ApiBaseModel):
    """管理员创建用户"""
    email: EmailStr
    password: str = Field(..., min_length=8)
    role: UserRole = UserRole.USER


class AdminUserUpdate(_ApiBaseModel):
    """管理员更新用户"""
    email: Optional[EmailStr] = None
    role: Optional[UserRole] = None
    is_active: Optional[bool] = None


class UserListResponse(_ApiBaseModel):
    """用户列表响应"""
    total: int
    page: int
    page_size: int
    items: List[UserResponse]


class QuestionListResponse(_ApiBaseModel):
    """题目列表响应"""
    total: int
    page: int
    page_size: int
    items: List[QuestionResponse]


class PaperSetListResponse(_ApiBaseModel):
    """组卷列表响应"""
    total: int
    page: int
    page_size: int
    items: List[PaperSetResponse]


class ApiCallLogResponse(_ApiBaseModel):
    """API 调用日志响应"""
    id: UUID
    user_id: Optional[UUID]
    user_email: Optional[str]
    purpose: str
    provider: Optional[str]
    model_name: Optional[str]
    cost_usd: float
    status_code: Optional[int]
    latency_ms: Optional[int]
    created_at: datetime
    # 添加别名以兼容前端
    total_tokens: Optional[int] = None
    prompt_tokens: Optional[int] = None
    completion_tokens: Optional[int] = None


class ApiCallLogListResponse(_ApiBaseModel):
    """API 调用日志列表响应"""
    total: int
    page: int
    page_size: int
    summary: dict
    items: List[ApiCallLogResponse]


class ApiCallStatsResponse(_ApiBaseModel):
    """API 调用统计响应"""
    total_calls: int
    total_cost_usd: float
    avg_latency_ms: Optional[float]
    calls_by_provider: dict
    calls_by_model: dict
    calls_by_date: dict


# ==================== 用户管理 ====================

@router.get("/users", response_model=UserListResponse)
async def list_all_users(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: Optional[str] = None,
    role: Optional[UserRole] = None,
    is_active: Optional[bool] = None,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin)
):
    """获取所有用户列表（管理员）"""
    # 构建查询
    query = select(User)

    # 搜索过滤
    if search:
        search_condition = _build_expression_condition(
            search,
            lambda token: User.email.ilike(f"%{token}%"),
        )
        if search_condition is not None:
            query = query.where(search_condition)

    # 角色过滤
    if role:
        query = query.where(User.role == role)

    # 状态过滤
    if is_active is not None:
        query = query.where(User.is_active == is_active)

    # 获取总数
    total_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(total_query)
    total = total_result.scalar() or 0

    # 分页
    query = query.order_by(desc(User.created_at))
    query = query.offset((page - 1) * page_size).limit(page_size)

    # 执行查询
    result = await db.execute(query)
    users = result.scalars().all()

    return UserListResponse(
        total=total,
        page=page,
        page_size=page_size,
        items=[
            UserResponse(
                id=user.id,
                email=user.email,
                role=user.role,
                is_active=user.is_active,
                created_at=user.created_at,
                updated_at=user.updated_at
            )
            for user in users
        ]
    )


@router.get("/users/{user_id}", response_model=UserResponse)
async def get_user_detail(
    user_id: UUID,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin)
):
    """获取用户详情（管理员）"""
    result = await db.execute(
        select(User).where(User.id == user_id)
    )
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")

    return UserResponse(
        id=user.id,
        email=user.email,
        role=user.role,
        is_active=user.is_active,
        created_at=user.created_at,
        updated_at=user.updated_at
    )


@router.post("/users", response_model=UserResponse)
async def create_user(
    user_data: AdminUserCreate,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin)
):
    """创建用户（管理员）"""
    # 检查邮箱是否已存在
    result = await db.execute(
        select(User).where(User.email == user_data.email)
    )
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="邮箱已存在")

    # 创建用户
    user = User(
        email=user_data.email,
        password_hash=get_password_hash(user_data.password),
        role=user_data.role
    )

    db.add(user)
    await db.commit()
    await db.refresh(user)

    return UserResponse(
        id=user.id,
        email=user.email,
        role=user.role,
        is_active=user.is_active,
        created_at=user.created_at,
        updated_at=user.updated_at
    )


@router.patch("/users/{user_id}/role", response_model=UserResponse)
async def update_user_role(
    user_id: UUID,
    role_data: dict,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin)
):
    """更新用户角色（管理员）"""
    result = await db.execute(
        select(User).where(User.id == user_id)
    )
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")

    # 更新角色
    if 'role' in role_data:
        user.role = role_data['role']

    await db.commit()
    await db.refresh(user)

    return UserResponse(
        id=user.id,
        email=user.email,
        role=user.role,
        is_active=user.is_active,
        created_at=user.created_at,
        updated_at=user.updated_at
    )


@router.put("/users/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: UUID,
    user_data: AdminUserUpdate,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin)
):
    """更新用户（管理员）"""
    result = await db.execute(
        select(User).where(User.id == user_id)
    )
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")

    # 更新字段
    if user_data.email is not None:
        # 检查新邮箱是否已被其他用户使用
        existing = await db.execute(
            select(User).where(
                User.email == user_data.email,
                User.id != user_id
            )
        )
        if existing.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="邮箱已被使用")
        user.email = user_data.email

    if user_data.role is not None:
        user.role = user_data.role

    if user_data.is_active is not None:
        user.is_active = user_data.is_active

    await db.commit()
    await db.refresh(user)

    return UserResponse(
        id=user.id,
        email=user.email,
        role=user.role,
        is_active=user.is_active,
        created_at=user.created_at,
        updated_at=user.updated_at
    )


@router.delete("/users/{user_id}")
async def delete_user(
    user_id: UUID,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin)
):
    """删除用户（管理员）"""
    result = await db.execute(
        select(User).where(User.id == user_id)
    )
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")

    if user.id == admin.id:
        raise HTTPException(status_code=400, detail="不能删除自己")

    await db.delete(user)
    await db.commit()

    return {"message": "用户已删除"}


# ==================== 总题库管理 ====================

@router.get("/questions", response_model=QuestionListResponse)
async def list_all_questions(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    user_id: Optional[UUID] = None,
    user: Optional[str] = None,
    subject: Optional[str] = None,
    book_name: Optional[str] = None,
    chapter_name: Optional[str] = None,
    type: Optional[str] = None,
    difficulty: Optional[str] = None,
    knowledge_point_q: Optional[str] = None,
    search: Optional[str] = None,
    q: Optional[str] = None,
    tags_json: Optional[List[str]] = Query(None),
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin)
):
    """获取所有题目列表（管理员）"""
    # 构建查询
    query = select(Question).where(Question.is_deleted == False)

    # 用户过滤
    if user_id:
        query = query.where(Question.user_id == user_id)

    # 按用户（ID或邮箱关键词）筛选
    if user:
        user_conditions = []
        try:
            user_conditions.append(Question.user_id == UUID(user))
        except ValueError:
            pass

        user_email_conditions = _build_expression_condition(
            user,
            lambda token: User.email.ilike(f"%{token}%"),
        )
        user_lookup_query = select(User.id)
        if user_email_conditions is not None:
            user_lookup_query = user_lookup_query.where(user_email_conditions)
        user_rows = await db.execute(user_lookup_query)
        matched_user_ids = [row.id for row in user_rows]
        if matched_user_ids:
            user_conditions.append(Question.user_id.in_(matched_user_ids))

        if user_conditions:
            query = query.where(or_(*user_conditions))
        else:
            query = query.where(false())

    # 学科过滤
    if subject:
        query = query.where(Question.subject == subject)

    # 来源筛选
    if book_name:
        book_condition = _build_expression_condition(
            book_name,
            lambda token: Question.book_name.ilike(f"%{token}%"),
        )
        if book_condition is not None:
            query = query.where(book_condition)

    if chapter_name:
        chapter_condition = _build_expression_condition(
            chapter_name,
            lambda token: Question.chapter_name.ilike(f"%{token}%"),
        )
        if chapter_condition is not None:
            query = query.where(chapter_condition)

    # 题型过滤
    if type:
        query = query.where(Question.type == type)

    # 难度过滤
    if difficulty:
        query = query.where(Question.difficulty == difficulty)

    if knowledge_point_q:
        knowledge_condition = _build_expression_condition(
            knowledge_point_q,
            lambda token: cast(Question.knowledge_points_json, String).ilike(f"%{token}%"),
        )
        if knowledge_condition is not None:
            query = query.where(knowledge_condition)

    # 标签过滤（需包含所有标签）
    if tags_json:
        for tag in tags_json:
            query = query.where(Question.tags_json.contains([tag]))

    # 创建时间过滤
    if start_date:
        query = query.where(Question.created_at >= start_date)
    if end_date:
        query = query.where(Question.created_at <= end_date)

    # 搜索过滤
    keyword = search or q
    if keyword:
        keyword_condition = _build_expression_condition(
            keyword,
            lambda token: or_(
                Question.stem_text.ilike(f"%{token}%"),
                Question.stem_latex.ilike(f"%{token}%"),
                Question.appendix.ilike(f"%{token}%"),
            )
        )
        if keyword_condition is not None:
            query = query.where(keyword_condition)

    # 获取总数
    total_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(total_query)
    total = total_result.scalar() or 0

    # 分页
    query = query.order_by(desc(Question.created_at))
    query = query.offset((page - 1) * page_size).limit(page_size)

    # 执行查询
    result = await db.execute(query)
    questions = result.scalars().all()

    user_ids = list({q.user_id for q in questions})
    user_email_map = {}
    if user_ids:
        user_result = await db.execute(
            select(User.id, User.email).where(User.id.in_(user_ids))
        )
        user_email_map = {row.id: row.email for row in user_result}

    # 构建响应
    items = []
    for q in questions:
        items.append(QuestionResponse(
            id=q.id,
            user_id=q.user_id,
            created_by=user_email_map.get(q.user_id),
            paper_id=q.paper_id,
            subject=q.subject,
            book_name=q.book_name,
            chapter_name=q.chapter_name,
            page_no=q.page_no,
            question_no=q.question_no,
            source_anchor=q.source_anchor,
            type=q.type,
            difficulty=q.difficulty,
            stem_text=q.stem_text,
            stem_latex=q.stem_latex,
            appendix=q.appendix,
            content_json=q.content_json,
            paper_meta=q.paper_meta,
            tags_json=q.tags_json,
            from_extraction_id=q.from_extraction_id,
            is_deleted=q.is_deleted,
            created_at=q.created_at,
            updated_at=q.updated_at,
            stem_images=[]  # TODO: 加载图片
        ))

    return QuestionListResponse(
        total=total,
        page=page,
        page_size=page_size,
        items=items
    )


# ==================== 总组卷管理 ====================

@router.get("/paper-sets", response_model=PaperSetListResponse)
async def list_all_paper_sets(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    user_id: Optional[UUID] = None,
    subject: Optional[str] = None,
    search: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin)
):
    """获取所有组卷列表（管理员）"""
    # 构建查询
    query = select(PaperSet)

    # 用户过滤
    if user_id:
        query = query.where(PaperSet.user_id == user_id)

    # 学科过滤
    if subject:
        query = query.where(PaperSet.subject == subject)

    # 搜索过滤
    if search:
        search_condition = _build_expression_condition(
            search,
            lambda token: PaperSet.title.ilike(f"%{token}%"),
        )
        if search_condition is not None:
            query = query.where(search_condition)

    # 获取总数
    total_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(total_query)
    total = total_result.scalar() or 0

    # 分页
    query = query.order_by(desc(PaperSet.created_at))
    query = query.offset((page - 1) * page_size).limit(page_size)

    # 执行查询
    result = await db.execute(query)
    paper_sets = result.scalars().all()

    # 获取所有组卷的题目数量（单次查询）
    from api.models.paper_set_item import PaperSetItem
    paper_set_ids = [ps.id for ps in paper_sets]
    if paper_set_ids:
        count_query = select(
            PaperSetItem.paper_set_id,
            func.count(PaperSetItem.question_id).label('count')
        ).where(
            PaperSetItem.paper_set_id.in_(paper_set_ids)
        ).group_by(PaperSetItem.paper_set_id)

        count_result = await db.execute(count_query)
        count_map = {row.paper_set_id: row.count for row in count_result}
    else:
        count_map = {}

    # 构建响应
    items = []
    for ps in paper_sets:
        question_count = count_map.get(ps.id, 0)

        items.append(PaperSetResponse(
            id=ps.id,
            user_id=ps.user_id,
            title=ps.title,
            subject=ps.subject,
            description=ps.description,
            output_format=ps.output_format,
            render_options=ps.render_options,
            question_count=question_count,
            created_at=ps.created_at,
            updated_at=ps.updated_at
        ))

    return PaperSetListResponse(
        total=total,
        page=page,
        page_size=page_size,
        items=items
    )


# ==================== API 使用日志 ====================

@router.get("/api-logs", response_model=ApiCallLogListResponse)
async def list_api_logs(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    user_id: Optional[UUID] = None,
    purpose: Optional[str] = None,
    provider: Optional[str] = None,
    search: Optional[str] = None,
    start_day: Optional[date] = None,
    end_day: Optional[date] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin)
):
    """获取 API 调用日志列表（管理员）"""
    # 构建查询
    query = select(ApiCallLog)

    # 用户过滤
    if user_id:
        query = query.where(ApiCallLog.user_id == user_id)

    # 用途过滤
    if purpose:
        query = query.where(ApiCallLog.purpose.ilike(f"%{purpose}%"))

    # 提供商过滤
    if provider:
        query = query.where(ApiCallLog.provider == provider)

    if search:
        search_condition = _build_expression_condition(
            search,
            lambda token: or_(
                ApiCallLog.purpose.ilike(f"%{token}%"),
                ApiCallLog.provider.ilike(f"%{token}%"),
                ApiCallLog.model_name.ilike(f"%{token}%"),
            )
        )
        if search_condition is not None:
            query = query.where(search_condition)

    # 日期范围过滤
    effective_start_date = start_date
    effective_end_date = end_date
    if start_day:
        effective_start_date = datetime.combine(start_day, time.min)
    if end_day:
        effective_end_date = datetime.combine(end_day, time.max)

    if effective_start_date:
        query = query.where(ApiCallLog.created_at >= effective_start_date)
    if effective_end_date:
        query = query.where(ApiCallLog.created_at <= effective_end_date)

    # 获取总数
    total_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(total_query)
    total = total_result.scalar() or 0

    total_cost_query = select(func.coalesce(func.sum(ApiCallLog.cost_usd), 0)).select_from(query.subquery())
    total_cost_result = await db.execute(total_cost_query)
    total_cost = total_cost_result.scalar() or 0

    # 分页
    query = query.order_by(desc(ApiCallLog.created_at))
    query = query.offset((page - 1) * page_size).limit(page_size)

    # 执行查询
    result = await db.execute(query)
    logs = result.scalars().all()

    # 获取用户邮箱和提取 token 信息
    user_ids = list({log.user_id for log in logs if log.user_id})
    user_email_map: dict[UUID, str] = {}
    if user_ids:
        user_rows = await db.execute(select(User.id, User.email).where(User.id.in_(user_ids)))
        user_email_map = {row.id: row.email for row in user_rows}

    items = []
    for log in logs:
        user_email = user_email_map.get(log.user_id) if log.user_id else None

        # 从 usage_json 中提取 token 信息
        usage_json = log.usage_json if isinstance(log.usage_json, dict) else {}
        total_tokens = usage_json.get('total_tokens') if usage_json else None
        prompt_tokens = usage_json.get('prompt_tokens') if usage_json else None
        completion_tokens = usage_json.get('completion_tokens') if usage_json else None

        items.append(ApiCallLogResponse(
            id=log.id,
            user_id=log.user_id,
            user_email=user_email,
            purpose=log.purpose,
            provider=log.provider,
            model_name=log.model_name,
            cost_usd=float(log.cost_usd) if log.cost_usd else 0,
            status_code=log.status_code,
            latency_ms=log.latency_ms,
            created_at=log.created_at,
            total_tokens=total_tokens,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens
        ))

    return ApiCallLogListResponse(
        total=total,
        page=page,
        page_size=page_size,
        summary={
            "total_calls": total,
            "total_cost_usd": float(total_cost),
        },
        items=items
    )


@router.get("/api-logs/stats", response_model=ApiCallStatsResponse)
async def get_api_stats(
    start_day: Optional[date] = None,
    end_day: Optional[date] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin)
):
    """获取 API 调用统计（管理员）"""
    # 默认统计最近 30 天
    if start_day:
        start_date = datetime.combine(start_day, time.min)
    if end_day:
        end_date = datetime.combine(end_day, time.max)
    if not start_date:
        start_date = utcnow() - timedelta(days=30)
    if not end_date:
        end_date = utcnow()

    # 构建基础查询
    base_query = select(ApiCallLog).where(
        ApiCallLog.created_at >= start_date,
        ApiCallLog.created_at <= end_date
    )

    # 总调用次数
    total_calls_result = await db.execute(
        select(func.count()).select_from(base_query.subquery())
    )
    total_calls = total_calls_result.scalar() or 0

    # 总成本
    total_cost_result = await db.execute(
        select(func.sum(ApiCallLog.cost_usd)).select_from(base_query.subquery())
    )
    total_cost = total_cost_result.scalar() or 0

    # 平均延迟
    avg_latency_result = await db.execute(
        select(func.avg(ApiCallLog.latency_ms)).select_from(base_query.subquery())
    )
    avg_latency = avg_latency_result.scalar()

    # 按提供商统计
    provider_stats = await db.execute(
        select(
            ApiCallLog.provider,
            func.count().label('count'),
            func.sum(ApiCallLog.cost_usd).label('cost')
        ).where(
            ApiCallLog.created_at >= start_date,
            ApiCallLog.created_at <= end_date
        ).group_by(ApiCallLog.provider)
    )
    calls_by_provider = {
        row.provider or "unknown": {
            "count": row.count,
            "cost": float(row.cost) if row.cost else 0
        }
        for row in provider_stats
    }

    # 按模型统计
    model_stats = await db.execute(
        select(
            ApiCallLog.model_name,
            func.count().label('count'),
            func.sum(ApiCallLog.cost_usd).label('cost')
        ).where(
            ApiCallLog.created_at >= start_date,
            ApiCallLog.created_at <= end_date
        ).group_by(ApiCallLog.model_name)
    )
    calls_by_model = {
        row.model_name or "unknown": {
            "count": row.count,
            "cost": float(row.cost) if row.cost else 0
        }
        for row in model_stats
    }

    # 按日期统计
    date_stats = await db.execute(
        select(
            func.date(ApiCallLog.created_at).label('date'),
            func.count().label('count'),
            func.sum(ApiCallLog.cost_usd).label('cost')
        ).where(
            ApiCallLog.created_at >= start_date,
            ApiCallLog.created_at <= end_date
        ).group_by(func.date(ApiCallLog.created_at))
        .order_by(func.date(ApiCallLog.created_at))
    )
    calls_by_date = {
        str(row.date): {
            "count": row.count,
            "cost": float(row.cost) if row.cost else 0
        }
        for row in date_stats
    }

    return ApiCallStatsResponse(
        total_calls=total_calls,
        total_cost_usd=float(total_cost),
        avg_latency_ms=avg_latency,
        calls_by_provider=calls_by_provider,
        calls_by_model=calls_by_model,
        calls_by_date=calls_by_date
    )
