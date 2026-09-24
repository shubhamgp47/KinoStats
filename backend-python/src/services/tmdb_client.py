"""
Asynchronous TMDB API Client for KinoStats.
Implements non-blocking HTTP requests with concurrency throttling via asyncio.Semaphore.
"""

import asyncio
import logging
from typing import Optional
import httpx
from src.core.config import settings
from src.schemas.tmdb import (
    TmdbMovieDetails,
    TmdbPersonCreditsResponse,
    TmdbSearchResponse,
)

logger = logging.getLogger(__name__)


class TmdbAsyncClient:
    """
    Thread-safe, non-blocking TMDB API Client.
    Protects downstream TMDB endpoints from HTTP 429 errors using an AsyncIO Semaphore.
    """

    def __init__(self, api_key: str = settings.TMDB_API_KEY, base_url: str = settings.TMDB_API_URL):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        
        # Concurrency limiter: Allow at most 10 concurrent requests to TMDB
        self._rate_limiter = asyncio.Semaphore(10)
        
        # Reusable AsyncClient with configured connection pools and headers
        self._client = httpx.AsyncClient(
            base_url=self.base_url,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Accept": "application/json",
            },
            timeout=httpx.Timeout(10.0, connect=5.0),
            limits=httpx.Limits(max_keepalive_connections=20, max_connections=50),
        )

    async def close(self) -> None:
        """Gracefully release HTTP connection pools during application shutdown."""
        await self._client.aclose()

    async def search_movie(self, title: str, year: int) -> Optional[int]:
        """
        Search TMDB for a movie by title and exact release year.
        Returns the TMDB movie ID if found, otherwise None.
        """
        async with self._rate_limiter:
            # Yield control back to the event loop for 25ms to smooth request bursts
            await asyncio.sleep(0.025)
            try:
                response = await self._client.get(
                    "/search/movie",
                    params={
                        "query": title,
                        "year": year,
                        "include_adult": "false",
                    },
                )
                response.raise_for_status()
                data = TmdbSearchResponse.model_validate(response.json())
                
                if data.results:
                    return data.results[0].id
                return None
                
            except httpx.HTTPStatusError as exc:
                logger.error("TMDB search returned HTTP %d for '%s' (%d)", exc.response.status_code, title, year)
                return None
            except Exception as exc:
                logger.error("Failed to query TMDB search for '%s' (%d): %s", title, year, str(exc))
                return None

    async def get_movie_details(self, tmdb_id: int) -> Optional[TmdbMovieDetails]:
        """
        Fetch full movie metadata including crew/directors in a single network round-trip
        via TMDB's 'append_to_response=credits'.
        """
        async with self._rate_limiter:
            await asyncio.sleep(0.025)
            try:
                response = await self._client.get(
                    f"/movie/{tmdb_id}",
                    params={"append_to_response": "credits"},
                )
                response.raise_for_status()
                return TmdbMovieDetails.model_validate(response.json())
                
            except httpx.HTTPStatusError as exc:
                logger.error("TMDB details returned HTTP %d for ID %d", exc.response.status_code, tmdb_id)
                return None
            except Exception as exc:
                logger.error("Failed to fetch TMDB details for ID %d: %s", tmdb_id, str(exc))
                return None

    async def get_director_canon_count(self, tmdb_person_id: int) -> int:
        """
        Fetch total canonical feature films directed by a person from TMDB /person/{id}/movie_credits.
        Filters for items where department='Directing' and job='Director'.
        """
        async with self._rate_limiter:
            await asyncio.sleep(0.025)
            try:
                response = await self._client.get(f"/person/{tmdb_person_id}/movie_credits")
                response.raise_for_status()
                data = TmdbPersonCreditsResponse.model_validate(response.json())
                
                # Filter for Directing department and distinct movie IDs
                canon_movie_ids = {
                    credit.id
                    for credit in data.crew
                    if (credit.department or "").lower() == "directing"
                    and (credit.job or "").lower() == "director"
                }
                return len(canon_movie_ids)
                
            except Exception as exc:
                logger.error("Failed to fetch canonical film count for person ID %d: %s", tmdb_person_id, str(exc))
                return 0


# Global Singleton Client Instance
tmdb_client = TmdbAsyncClient()