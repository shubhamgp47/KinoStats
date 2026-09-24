"""
REST API Controller for Cinema Statistics and Director Completion.
Matches com.cinestats.backend_java.controller.StatsController.
"""

from collections.abc import Sequence
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.deps import get_current_user
from src.core.database import get_db
from src.models.entities import User
from src.schemas.stats import (
    DirectorProgressResponse,
    GenreStatResponse,
    StatsOverviewResponse,
)
from src.services.stats_engine import stats_engine

router = APIRouter()


@router.get(
    "/stats/overview",
    response_model=StatsOverviewResponse,
    summary="Get user lifetime viewing overview metrics",
)
async def get_stats_overview(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Returns total watch count, total hours, average rating, and top decade."""
    return await stats_engine.get_overview(user.id, db)


@router.get(
    "/stats/genres",
    response_model=Sequence[GenreStatResponse],
    summary="Get user genre distribution breakdown",
)
async def get_genre_stats(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Returns film counts and average rating aggregated across all genres."""
    return await stats_engine.get_genre_stats(user.id, db)


@router.get(
    "/stats/directors/completionist",
    response_model=Sequence[DirectorProgressResponse],
    summary="Get director filmography completion percentages",
)
async def get_director_completion(
    limit: int = Query(default=8, ge=1, le=50, description="Number of directors to return"),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Calculates top directors ranked by films watched, tracking progress against
    canonical lifetime feature films with Letterboxd deep-links.
    """
    return await stats_engine.get_top_directors(user=user, limit=limit, db=db)