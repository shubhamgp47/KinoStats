"""
Pydantic models for unmarshalling external TMDB JSON responses.
Matches Java records: TmdbSearchResponse, TmdbMovieDetails, and TmdbPersonCredits.
"""

from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field


class TmdbGenreItem(BaseModel):
    """Genre node from TMDB movie details payload."""
    id: int
    name: str


class TmdbCrewMember(BaseModel):
    """Crew node used to isolate the primary director."""
    id: int
    name: str
    job: Optional[str] = None
    department: Optional[str] = None
    profile_path: Optional[str] = Field(None, alias="profile_path")

    model_config = ConfigDict(extra="ignore")


class TmdbCreditsContainer(BaseModel):
    """Credits container returned by 'append_to_response=credits'."""
    crew: List[TmdbCrewMember] = []

    model_config = ConfigDict(extra="ignore")


class TmdbMovieSearchResult(BaseModel):
    """Minimal movie result from TMDB /search/movie."""
    id: int
    title: str
    release_date: Optional[str] = None

    model_config = ConfigDict(extra="ignore")


class TmdbSearchResponse(BaseModel):
    """Root search response envelope from TMDB."""
    results: List[TmdbMovieSearchResult] = []

    model_config = ConfigDict(extra="ignore")


class TmdbMovieDetails(BaseModel):
    """
    Complete enriched movie metadata payload.
    Includes runtime, posters, genres, and credits.
    """
    id: int
    title: str
    runtime: Optional[int] = 0
    poster_path: Optional[str] = None
    backdrop_path: Optional[str] = None
    overview: Optional[str] = None
    genres: List[TmdbGenreItem] = []
    credits: Optional[TmdbCreditsContainer] = None

    model_config = ConfigDict(extra="ignore")


class TmdbPersonMovieCredit(BaseModel):
    """Credit node from TMDB /person/{id}/movie_credits used for canonical counts."""
    id: int
    title: Optional[str] = None
    department: Optional[str] = None
    job: Optional[str] = None

    model_config = ConfigDict(extra="ignore")


class TmdbPersonCreditsResponse(BaseModel):
    """Root credits envelope for a person/director."""
    crew: List[TmdbPersonMovieCredit] = []

    model_config = ConfigDict(extra="ignore")