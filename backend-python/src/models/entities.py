"""
SQLAlchemy 2.0 Declarative Models for KinoStats.
Maps to V1 and V2 PostgreSQL schema tables with foreign key cascades and check constraints.
"""

from datetime import date, datetime
from decimal import Decimal
from typing import List, Optional
import uuid

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    Column,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    SmallInteger,
    String,
    Table,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from src.core.database import Base


# ============================================================================
# Association / Join Tables (Many-to-Many Relationships)
# ============================================================================

# Matches SQL: CREATE TABLE movie_genres (movie_id BIGINT, genre_id SMALLINT)
movie_genres = Table(
    "movie_genres",
    Base.metadata,
    Column("movie_id", BigInteger, ForeignKey("movies.id", ondelete="CASCADE"), primary_key=True),
    Column("genre_id", SmallInteger, ForeignKey("genres.id", ondelete="CASCADE"), primary_key=True),
)

# Matches SQL: CREATE TABLE movie_directors (movie_id BIGINT, director_id BIGINT)
movie_directors = Table(
    "movie_directors",
    Base.metadata,
    Column("movie_id", BigInteger, ForeignKey("movies.id", ondelete="CASCADE"), primary_key=True),
    Column("director_id", BigInteger, ForeignKey("directors.id", ondelete="CASCADE"), primary_key=True),
)


# ============================================================================
# Entity Models
# ============================================================================

class User(Base):
    """
    Tenant entity representing Letterboxd users (guest sessions or registered accounts).
    """
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=func.gen_random_uuid(),
    )
    letterboxd_username: Mapped[str] = mapped_column(String(100), nullable=False)
    session_token: Mapped[Optional[str]] = mapped_column(String(255), unique=True, nullable=True)
    is_guest: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.current_timestamp(), nullable=False
    )
    last_active_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.current_timestamp(), nullable=False
    )

    # 1-to-Many relationship with watch history
    watch_logs: Mapped[List["WatchLog"]] = relationship(
        "WatchLog", back_populates="user", cascade="all, delete-orphan"
    )


class Genre(Base):
    """Normalized movie genre catalog (synced with TMDB genre IDs)."""
    __tablename__ = "genres"

    id: Mapped[int] = mapped_column(SmallInteger, primary_key=True, autoincrement=True)
    tmdb_genre_id: Mapped[int] = mapped_column(Integer, unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)

    movies: Mapped[List["Movie"]] = relationship(
        "Movie", secondary=movie_genres, back_populates="genres", lazy="selectin"
    )


class Director(Base):
    """
    Normalized director entity tracking TMDB ID and canonical feature film counts.
    Matches Flyway V1 + V2 schema additions.
    """
    __tablename__ = "directors"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    tmdb_person_id: Mapped[int] = mapped_column(Integer, unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    profile_path: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    
    # Stores canonical lifetime feature count to prevent false 100% completion percentages
    total_directed: Mapped[int] = mapped_column(Integer, default=0, server_default="0", nullable=False)

    movies: Mapped[List["Movie"]] = relationship(
        "Movie", secondary=movie_directors, back_populates="directors", lazy="selectin"
    )


class Movie(Base):
    """
    Global shared movie catalog serving as the local cache.
    Eliminates redundant external calls to TMDB across different users.
    """
    __tablename__ = "movies"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    tmdb_id: Mapped[Optional[int]] = mapped_column(Integer, unique=True, nullable=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    release_year: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    runtime_minutes: Mapped[int] = mapped_column(SmallInteger, default=0, nullable=False)
    poster_path: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    backdrop_path: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    country_code: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    overview: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.current_timestamp(), nullable=False
    )

    # Relationships
    genres: Mapped[List[Genre]] = relationship(
        "Genre", secondary=movie_genres, back_populates="movies", lazy="selectin"
    )
    directors: Mapped[List[Director]] = relationship(
        "Director", secondary=movie_directors, back_populates="movies", lazy="selectin"
    )
    watch_logs: Mapped[List["WatchLog"]] = relationship("WatchLog", back_populates="movie")

    __table_args__ = (
        UniqueConstraint("title", "release_year", name="uq_movie_title_year"),
        Index("idx_movies_lookup", "title", "release_year"),
        Index("idx_movies_tmdb", "tmdb_id"),
    )


class WatchLog(Base):
    """
    Tenant-scoped event fact table linking a User with a Movie.
    Guards valid star ratings and prevents duplicate logs on the same date.
    """
    __tablename__ = "watch_logs"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    movie_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("movies.id", ondelete="RESTRICT"), nullable=False
    )
    watched_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    
    # Decimal(2, 1) to match SQL NUMERIC(2, 1). Unrated films persist as NULL.
    rating: Mapped[Optional[Decimal]] = mapped_column(Numeric(2, 1), nullable=True)
    is_rewatch: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    letterboxd_uri: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.current_timestamp(), nullable=False
    )

    # Relationships
    user: Mapped[User] = relationship("User", back_populates="watch_logs")
    movie: Mapped[Movie] = relationship("Movie", back_populates="watch_logs")

    __table_args__ = (
        CheckConstraint("rating >= 0.5 AND rating <= 5.0", name="watch_logs_rating_check"),
        UniqueConstraint("user_id", "movie_id", "watched_date", name="uq_user_movie_watch"),
        Index("idx_watch_logs_user_date", "user_id", "watched_date"),
        Index("idx_watch_logs_user_rating", "user_id", "rating"),
    )