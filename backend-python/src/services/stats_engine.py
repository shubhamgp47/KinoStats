"""
Analytical Statistics Engine for KinoStats.
Executes database-pushdown aggregations for user dashboards,
genre distributions, and director completion gauges.
"""

from collections.abc import Sequence
import logging
from typing import Optional
import uuid

from sqlalchemy import Row, desc, func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.entities import (
    Director,
    Genre,
    Movie,
    User,
    WatchLog,
    movie_directors,
    movie_genres,
)
from src.schemas.stats import (
    DirectorProgressResponse,
    GenreStatResponse,
    StatsOverviewResponse,
)

logger = logging.getLogger(__name__)


class StatsEngine:
    """
    Computes analytical aggregations directly in PostgreSQL.
    Matches the Spring Data JPA native query projections in WatchLogRepository.
    """

    async def get_overview(
        self, user_id: uuid.UUID, db: AsyncSession
    ) -> StatsOverviewResponse:
        """
        Calculates high-level lifetime viewing metrics:
          - Total films logged
          - Total hours watched (based on movie runtimes)
          - Lifetime average rating (excluding unrated NULL entries)
          - Most watched release year
          - Dominant decade
        """
        # 1. Scalar Aggregations: Total Watched, Total Minutes, Average Rating
        stmt_summary = (
            select(
                func.count(WatchLog.id).label("total_watched"),
                func.coalesce(func.sum(Movie.runtime_minutes), 0).label("total_minutes"),
                func.avg(WatchLog.rating).label("avg_rating"),
            )
            .join(Movie, WatchLog.movie_id == Movie.id)
            .where(WatchLog.user_id == user_id)
        )
        res_summary = await db.execute(stmt_summary)
        row_summary = res_summary.one()

        total_watched: int = row_summary.total_watched or 0
        total_minutes: int = row_summary.total_minutes or 0
        total_hours: float = round(total_minutes / 60.0, 1)
        average_rating: Optional[float] = (
            round(float(row_summary.avg_rating), 2)
            if row_summary.avg_rating is not None
            else None
        )

        # 2. Most Watched Release Year (Mode / Top-1 by count)
        stmt_top_year = (
            select(Movie.release_year, func.count(WatchLog.id).label("cnt"))
            .join(Movie, WatchLog.movie_id == Movie.id)
            .where(WatchLog.user_id == user_id)
            .group_by(Movie.release_year)
            .order_by(desc("cnt"), desc(Movie.release_year))
            .limit(1)
        )
        res_year = await db.execute(stmt_top_year)
        row_year = res_year.first()
        most_watched_year: Optional[int] = row_year[0] if row_year else None

        # 3. Dominant Decade: (release_year / 10) * 10 -> e.g. 2010s
        stmt_decade = (
            select(
                ((Movie.release_year / 10) * 10).label("decade_base"),
                func.count(WatchLog.id).label("cnt"),
            )
            .join(Movie, WatchLog.movie_id == Movie.id)
            .where(WatchLog.user_id == user_id)
            .group_by("decade_base")
            .order_by(desc("cnt"))
            .limit(1)
        )
        res_decade = await db.execute(stmt_decade)
        row_decade = res_decade.first()
        top_decade: Optional[str] = f"{int(row_decade[0])}s" if row_decade else None

        return StatsOverviewResponse(
            total_watched=total_watched,
            total_hours=total_hours,
            average_rating=average_rating,
            most_watched_year=most_watched_year,
            top_decade=top_decade,
        )

    async def get_genre_stats(
        self, user_id: uuid.UUID, db: AsyncSession
    ) -> Sequence[GenreStatResponse]:
        """
        Computes distribution of films and average rating grouped by genre.
        Pushes calculation to PostgreSQL to feed the Recharts GenreChart component.
        """
        stmt = (
            select(
                Genre.id.label("genre_id"),
                Genre.name.label("genre_name"),
                func.count(func.distinct(WatchLog.movie_id)).label("total_films"),
                func.avg(WatchLog.rating).label("average_rating"),
            )
            .join(movie_genres, movie_genres.c.genre_id == Genre.id)
            .join(WatchLog, WatchLog.movie_id == movie_genres.c.movie_id)
            .where(WatchLog.user_id == user_id)
            .group_by(Genre.id, Genre.name)
            .order_by(desc("total_films"), Genre.name.asc())
        )
        result = await db.execute(stmt)
        rows = result.all()

        return [
            GenreStatResponse(
                genre_id=row.genre_id,
                genre_name=row.genre_name,
                total_films=row.total_films,
                average_rating=(
                    round(float(row.average_rating), 2)
                    if row.average_rating is not None
                    else None
                ),
            )
            for row in rows
        ]

    async def get_top_directors(
        self,
        user: User,
        limit: int,
        db: AsyncSession,
    ) -> Sequence[DirectorProgressResponse]:
        """
        Calculates director completionist metrics.
        Guards against the Open-World Fallacy: calculates completion using
        d.total_directed (canonical count from TMDB) as the denominator,
        rather than locally cached movie counts.
        """
        # GREATEST(COALESCE(d.total_directed, 0), COUNT(DISTINCT wl.movie_id))
        # prevents completion percentages > 100% if canonical TMDB counts diverge.
        stmt = text("""
            SELECT 
                d.id AS director_id,
                d.name AS director_name,
                LOWER(REPLACE(REPLACE(d.name, ' ', '-'), '.', '')) AS slug,
                GREATEST(COALESCE(d.total_directed, 0), COUNT(DISTINCT wl.movie_id)) AS total_directed,
                COUNT(DISTINCT wl.movie_id) AS watched_count,
                ROUND(
                    (COUNT(DISTINCT wl.movie_id)::NUMERIC / 
                     NULLIF(GREATEST(COALESCE(d.total_directed, 0), COUNT(DISTINCT wl.movie_id)), 0)
                    ) * 100, 
                    1
                ) AS completion_percentage
            FROM watch_logs wl
            JOIN movies m ON wl.movie_id = m.id
            JOIN movie_directors md ON m.id = md.movie_id
            JOIN directors d ON md.director_id = d.id
            WHERE wl.user_id = :user_id
            GROUP BY d.id, d.name, d.total_directed
            ORDER BY watched_count DESC, completion_percentage DESC, d.name ASC
            LIMIT :limit
        """)

        result = await db.execute(stmt, {"user_id": user.id, "limit": limit})
        rows: Sequence[Row] = result.fetchall()

        # Build dynamic Letterboxd deep links
        # e.g., https://letterboxd.com/{username}/films/with/director/{slug}/
        clean_username = user.letterboxd_username.strip().lower()

        return [
            DirectorProgressResponse(
                director_id=row.director_id,
                director_name=row.director_name,
                slug=row.slug,
                total_directed=row.total_directed,
                watched_count=row.watched_count,
                completion_percentage=float(row.completion_percentage or 0.0),
                letterboxd_url=(
                    f"https://letterboxd.com/{clean_username}/films/with/director/{row.slug}/"
                ),
            )
            for row in rows
        ]


# Global Singleton Instance
stats_engine = StatsEngine()