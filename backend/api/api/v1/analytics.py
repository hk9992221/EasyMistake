from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from api.core.deps import get_db, get_current_user
from api.models.user import User
from api.schemas.analytics import (
    AnalyticsOverviewResponse,
    ErrorTagsStatsResponse,
    MasteryDistributionResponse,
    KnowledgePointStatsResponse,
    ReviewRetentionResponse,
)
from api.services.analytics_service import analytics_service


router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/overview", response_model=AnalyticsOverviewResponse)
async def get_analytics_overview(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await analytics_service.overview(db, current_user.id)


@router.get("/error-tags", response_model=ErrorTagsStatsResponse)
async def get_error_tags_stats(
    top: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await analytics_service.error_tags(db, current_user.id, top=top)


@router.get("/knowledge-points", response_model=KnowledgePointStatsResponse)
async def get_knowledge_points_stats(
    top: int = Query(30, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await analytics_service.knowledge_points(db, current_user.id, top=top)


@router.get("/review-retention", response_model=ReviewRetentionResponse)
async def get_review_retention(
    days: int = Query(30, ge=1, le=365),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await analytics_service.review_retention(db, current_user.id, days=days)


@router.get("/questions/mastery-distribution", response_model=MasteryDistributionResponse)
async def get_mastery_distribution(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await analytics_service.mastery_distribution(db, current_user.id)
