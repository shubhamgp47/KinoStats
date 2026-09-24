"""
Ingestion Service for KinoStats.
Implements the Database-First Lazy-Cache Pattern, concurrent TMDB resolution,
and idempotent batch ingestion for Letterboxd export files.
"""

import asyncio
from datetime import datetime, timezone
from decimal import Decimal
import logging
from typing import Dict, List, Optional, Set, Tuple
import uuid

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
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
from src.schemas.imports import DiaryEntryDto, ImportResponse, LetterboxdImportRequest
from src.services.tmdb_client import tmdb_client

logger = logging.getLogger(__name__)


class IngestionService:
    """
    Coordinates user resolution, cache matching, TMDB metadata enrichment,
    and idempotent persistence of watch logs.
    """

    async def process_import(
        self,
        payload: LetterboxdImportRequest,
        session_token: Optional[str],
        db: AsyncSession,
    ) -> ImportResponse:
        """
        Main entry point for Letterboxd file ingestion.
        Runs the Database-First Lazy-Cache workflow.
        """
        logger.info(
            "Starting Letterboxd import for user '%s' with %d entries",
            payload.username,
            len(payload.entries),
        )

        # 1. Resolve or create tenant user
        user = await self._resolve_or_create_user(payload.username, session_token, db)

        # 2. Partition incoming entries into cache hits vs cache misses
        total_received = len(payload.entries)
        cache_hits, cache_misses, resolved_movies = await self._partition_cache(
            payload.entries, db
        )
        logger.info(
            "Cache Partition Complete: %d hits, %d misses to fetch from TMDB",
            cache_hits,
            len(cache_misses),
        )

        # 3. Concurrently enrich cache misses via TMDB if any exist
        enriched_count = 0
        if cache_misses:
            logger.info("Resolving %d misses concurrently via AsyncIO...", len(cache_misses))
            enriched_count = await self._resolve_misses_concurrently(
                cache_misses, resolved_movies, db
            )

        # 4. Batch persist watch logs with idempotency guards
        await self._persist_watch_logs(user, payload.entries, resolved_movies, db)
        logger.info("Watch logs successfully committed for user '%s'", user.letterboxd_username)

        return ImportResponse(
            total_received=total_received,
            matched_in_cache=cache_hits,
            queued_for_enrichment=enriched_count,
            user_id=user.id,
            session_token=user.session_token,
        )

    async def _resolve_or_create_user(
        self, username: str, session_token: Optional[str], db: AsyncSession
    ) -> User:
        """
        Finds existing user by session token or username.
        Provisions a new guest UUID session if not found.
        """
        if session_token:
            stmt = select(User).where(User.session_token == session_token)
            result = await db.execute(stmt)
            existing_user = result.scalar_one_or_none()
            if existing_user:
                existing_user.last_active_at = datetime.now(timezone.utc)
                await db.flush()
                return existing_user

        # Lookup by username fallback
        stmt = select(User).where(User.letterboxd_username == username)
        result = await db.execute(stmt)
        user = result.scalar_one_or_none()

        if not user:
            user = User(
                letterboxd_username=username,
                session_token=str(uuid.uuid4()),
                is_guest=True,
                last_active_at=datetime.now(timezone.utc),
            )
            db.add(user)
            await db.flush()  # Populates user.id without committing outer transaction
        else:
            user.last_active_at = datetime.now(timezone.utc)
            await db.flush()

        return user

    async def _partition_cache(
        self, entries: List[DiaryEntryDto], db: AsyncSession
    ) -> Tuple[int, List[DiaryEntryDto], Dict[str, Movie]]:
        """
        Queries the local PostgreSQL movies table using case-insensitive title and year.
        Returns:
            (cache_hit_count, list_of_cache_misses, map_of_resolved_movies)
        """
        cache_hits = 0
        cache_misses: List[DiaryEntryDto] = []
        resolved_movies: Dict[str, Movie] = {}
        seen_keys: Set[str] = set()

        for entry in entries:
            cache_key = f"{entry.title.strip().lower()}_{entry.release_year}"

            # Avoid redundant DB queries if duplicate films exist in same batch
            if cache_key in seen_keys:
                continue
            seen_keys.add(cache_key)

            # Query Postgres local cache
            stmt = select(Movie).where(
                func.lower(Movie.title) == entry.title.strip().lower(),
                Movie.release_year == entry.release_year,
            )
            result = await db.execute(stmt)
            movie = result.scalar_one_or_none()

            if movie:
                cache_hits += 1
                resolved_movies[cache_key] = movie
            else:
                cache_misses.append(entry)

        return cache_hits, cache_misses, resolved_movies

    async def _resolve_misses_concurrently(
        self,
        misses: List[DiaryEntryDto],
        resolved_movies: Dict[str, Movie],
        db: AsyncSession,
    ) -> int:
        """
        Uses asyncio.gather to resolve missing movie metadata concurrently from TMDB
        without blocking the ASGI event loop.
        """
        completed = 0
        total = len(misses)

        async def resolve_single_entry(entry: DiaryEntryDto):
            nonlocal completed
            cache_key = f"{entry.title.strip().lower()}_{entry.release_year}"

            if cache_key in resolved_movies:
                return

            # Search TMDB for movie ID
            tmdb_id = await tmdb_client.search_movie(entry.title, entry.release_year)
            if tmdb_id:
                details = await tmdb_client.get_movie_details(tmdb_id)
                if details:
                    saved_movie = await self._persist_enriched_movie(details, entry.release_year, db)
                    if saved_movie:
                        resolved_movies[cache_key] = saved_movie
            else:
                # Fallback Stub Pattern: Persist minimal record if TMDB has no match
                # Prevents dropped records and preserves exact watch counts
                saved_movie = await self._persist_stub_movie(entry.title, entry.release_year, db)
                if saved_movie:
                    resolved_movies[cache_key] = saved_movie

            completed += 1
            if completed % 25 == 0 or completed == total:
                logger.info("Ingestion Progress: [%d/%d] movies resolved from TMDB", completed, total)

        # Fire non-blocking coroutines concurrently
        await asyncio.gather(*(resolve_single_entry(entry) for entry in misses))
        return len(resolved_movies)

    async def _persist_stub_movie(self, title: str, release_year: int, db: AsyncSession) -> Optional[Movie]:
        """Creates a fallback movie stub when TMDB resolution fails."""
        stmt = (
            pg_insert(Movie)
            .values(
                title=title,
                release_year=release_year,
                runtime_minutes=0,
                tmdb_id=None,
            )
            .on_conflict_do_nothing(constraint="uq_movie_title_year")
            .returning(Movie)
        )
        result = await db.execute(stmt)
        movie = result.scalar_one_or_none()
        if not movie:
            # Already inserted by another concurrent coroutine
            stmt_select = select(Movie).where(
                func.lower(Movie.title) == title.strip().lower(),
                Movie.release_year == release_year,
            )
            res = await db.execute(stmt_select)
            movie = res.scalar_one_or_none()
        return movie

    async def _persist_enriched_movie(
        self, details, release_year: int, db: AsyncSession
    ) -> Optional[Movie]:
        """
        Persists movie, genres, directors, and associations using PostgreSQL UPSERT.
        Prevents Check-Then-Act race condition crashes (SQLState 23505).
        """
        # 1. Upsert Movie
        movie_stmt = (
            pg_insert(Movie)
            .values(
                tmdb_id=details.id,
                title=details.title,
                release_year=release_year,
                runtime_minutes=details.runtime or 0,
                poster_path=details.poster_path,
                backdrop_path=details.backdrop_path,
                overview=details.overview,
            )
            .on_conflict_do_nothing(index_elements=["tmdb_id"])
            .returning(Movie.id)
        )
        movie_res = await db.execute(movie_stmt)
        movie_id = movie_res.scalar_one_or_none()

        if not movie_id:
            # Fetch existing movie ID if conflict occurred
            existing_movie = await db.execute(select(Movie.id).where(Movie.tmdb_id == details.id))
            movie_id = existing_movie.scalar_one_or_none()

        if not movie_id:
            return None

        # 2. Upsert Genres & Junction Table
        if details.genres:
            for g in details.genres:
                genre_stmt = (
                    pg_insert(Genre)
                    .values(tmdb_genre_id=g.id, name=g.name)
                    .on_conflict_do_nothing(index_elements=["tmdb_genre_id"])
                    .returning(Genre.id)
                )
                genre_res = await db.execute(genre_stmt)
                genre_id = genre_res.scalar_one_or_none()

                if not genre_id:
                    existing_genre = await db.execute(select(Genre.id).where(Genre.tmdb_genre_id == g.id))
                    genre_id = existing_genre.scalar_one_or_none()

                if genre_id:
                    # Link in movie_genres join table
                    assoc_stmt = (
                        pg_insert(movie_genres)
                        .values(movie_id=movie_id, genre_id=genre_id)
                        .on_conflict_do_nothing()
                    )
                    await db.execute(assoc_stmt)

        # 3. Upsert Directors & Junction Table
        if details.credits and details.credits.crew:
            directors = [
                c for c in details.credits.crew
                if (c.job or "").lower() == "director"
            ]
            for d in directors:
                # Fetch canon feature film count from TMDB to prevent false 100% completion
                total_canon = await tmdb_client.get_director_canon_count(d.id)

                director_stmt = (
                    pg_insert(Director)
                    .values(
                        tmdb_person_id=d.id,
                        name=d.name,
                        profile_path=d.profile_path,
                        total_directed=total_canon if total_canon > 0 else 1,
                    )
                    .on_conflict_do_nothing(index_elements=["tmdb_person_id"])
                    .returning(Director.id)
                )
                director_res = await db.execute(director_stmt)
                director_id = director_res.scalar_one_or_none()

                if not director_id:
                    existing_director = await db.execute(
                        select(Director.id).where(Director.tmdb_person_id == d.id)
                    )
                    director_id = existing_director.scalar_one_or_none()

                if director_id:
                    # Link in movie_directors join table
                    assoc_stmt = (
                        pg_insert(movie_directors)
                        .values(movie_id=movie_id, director_id=director_id)
                        .on_conflict_do_nothing()
                    )
                    await db.execute(assoc_stmt)

        # Flush graph state
        await db.flush()

        # Return full model instance with preloaded relationships
        stmt_full = select(Movie).where(Movie.id == movie_id)
        result = await db.execute(stmt_full)
        return result.scalar_one_or_none()

    async def _persist_watch_logs(
        self,
        user: User,
        entries: List[DiaryEntryDto],
        resolved_movies: Dict[str, Movie],
        db: AsyncSession,
    ) -> None:
        """
        Deduplicates watch logs and commits them to watch_logs using PostgreSQL upsert.
        Protects against:
          1. Same-day duplicate entries in incoming file (in-memory deduplication set).
          2. Zero-rating CHECK constraint violations (coerces <= 0 to None / NULL).
          3. Re-import collisions with existing records (on_conflict_do_nothing).
        """
        logs_to_insert = []
        processed_keys_in_batch: Set[str] = set()

        for entry in entries:
            cache_key = f"{entry.title.strip().lower()}_{entry.release_year}"
            movie = resolved_movies.get(cache_key)

            if not movie:
                continue

            # Composite key: movie_id + watched_date (preserves legitimate rewatches on different days)
            unique_watch_key = f"{movie.id}_{entry.watched_date}"
            if unique_watch_key in processed_keys_in_batch:
                continue
            processed_keys_in_batch.add(unique_watch_key)

            # Convert 0.0 or non-positive ratings to None to satisfy DB CHECK constraint
            clean_rating: Optional[Decimal] = None
            if entry.rating is not None and entry.rating > Decimal("0.0"):
                clean_rating = entry.rating

            logs_to_insert.append({
                "user_id": user.id,
                "movie_id": movie.id,
                "watched_date": entry.watched_date,
                "rating": clean_rating,
                "is_rewatch": entry.is_rewatch,
                "letterboxd_uri": entry.letterboxd_uri,
            })

        if logs_to_insert:
            # Batch execute with ON CONFLICT DO NOTHING against constraint uq_user_movie_watch
            stmt = (
                pg_insert(WatchLog)
                .values(logs_to_insert)
                .on_conflict_do_nothing(
                    constraint="uq_user_movie_watch"
                )
            )
            await db.execute(stmt)
            await db.flush()


# Singleton Service Instance
ingestion_service = IngestionService()