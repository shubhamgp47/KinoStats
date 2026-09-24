"""
Pydantic v2 response models for cinema statistics and director filmography.
Matches Java projections and responses: StatsOverviewResponse, GenreStatResponse, DirectorProgressResponse.
"""

from typing import Optional
from pydantic import BaseModel, ConfigDict, Field


class StatsOverviewResponse(BaseModel):
    """High-level lifetime viewing summary for dashboard KPI metric cards."""
    total_watched: int = Field(..., alias="totalWatched")
    total_hours: float = Field(..., alias="totalHours")
    average_rating: Optional[float] = Field(None, alias="averageRating")
    most_watched_year: Optional[int] = Field(None, alias="mostWatchedYear")
    top_decade: Optional[str] = Field(None, alias="topDecade")

    model_config = ConfigDict(populate_by_name=True, from_attributes=True)


class GenreStatResponse(BaseModel):
    """Distribution metric row for Recharts GenreChart component."""
    genre_id: int = Field(..., alias="genreId")
    genre_name: str = Field(..., alias="genreName")
    total_films: int = Field(..., alias="totalFilms")
    average_rating: Optional[float] = Field(None, alias="averageRating")

    model_config = ConfigDict(populate_by_name=True, from_attributes=True)


class DirectorProgressResponse(BaseModel):
    """
    Filmography completion metric row for DirectorGauges component.
    Calculates progress against canonical feature films to avoid false 100% completions.
    """
    director_id: int = Field(..., alias="directorId")
    director_name: str = Field(..., alias="directorName")
    slug: str
    total_directed: int = Field(..., alias="totalDirected")
    watched_count: int = Field(..., alias="watchedCount")
    completion_percentage: float = Field(..., alias="completionPercentage")
    letterboxd_url: str = Field(..., alias="letterboxdUrl")

    model_config = ConfigDict(populate_by_name=True, from_attributes=True)