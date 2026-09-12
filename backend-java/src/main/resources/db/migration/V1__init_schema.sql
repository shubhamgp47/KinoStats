-- V1__init_schema.sql

-- 1. Users (Anonymous Guest UUIDs or Registered Accounts)
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    letterboxd_username VARCHAR(100) NOT NULL,
    session_token VARCHAR(255) UNIQUE,
    is_guest BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    last_active_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- 2. Master Movie Catalog (Shared Global Cache)
CREATE TABLE movies (
    id BIGSERIAL PRIMARY KEY,
    tmdb_id INTEGER UNIQUE,
    title VARCHAR(255) NOT NULL,
    release_year SMALLINT NOT NULL,
    runtime_minutes SMALLINT DEFAULT 0,
    poster_path VARCHAR(255),
    backdrop_path VARCHAR(255),
    country_code VARCHAR(10),
    overview TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_movie_title_year UNIQUE (title, release_year)
);

-- 3. Normalized Genres
CREATE TABLE genres (
    id SMALLSERIAL PRIMARY KEY,
    tmdb_genre_id INTEGER NOT NULL UNIQUE,
    name VARCHAR(50) NOT NULL UNIQUE
);

CREATE TABLE movie_genres (
    movie_id BIGINT NOT NULL REFERENCES movies(id) ON DELETE CASCADE,
    genre_id SMALLINT NOT NULL REFERENCES genres(id) ON DELETE CASCADE,
    PRIMARY KEY (movie_id, genre_id)
);

-- 4. Normalized Directors
CREATE TABLE directors (
    id BIGSERIAL PRIMARY KEY,
    tmdb_person_id INTEGER NOT NULL UNIQUE,
    name VARCHAR(150) NOT NULL,
    profile_path VARCHAR(255)
);

CREATE TABLE movie_directors (
    movie_id BIGINT NOT NULL REFERENCES movies(id) ON DELETE CASCADE,
    director_id BIGINT NOT NULL REFERENCES directors(id) ON DELETE CASCADE,
    PRIMARY KEY (movie_id, director_id)
);

-- 5. Tenant-Scoped User Watch Logs
CREATE TABLE watch_logs (
    id BIGSERIAL PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    movie_id BIGINT NOT NULL REFERENCES movies(id) ON DELETE RESTRICT,
    watched_date DATE,
    rating NUMERIC(2, 1) CHECK (rating >= 0.5 AND rating <= 5.0),
    is_rewatch BOOLEAN NOT NULL DEFAULT FALSE,
    letterboxd_uri VARCHAR(512),
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_user_movie_watch UNIQUE (user_id, movie_id, watched_date)
);

-- Analytical Indexing
CREATE INDEX idx_watch_logs_user_date ON watch_logs (user_id, watched_date DESC);
CREATE INDEX idx_watch_logs_user_rating ON watch_logs (user_id, rating);
CREATE INDEX idx_movies_lookup ON movies (title, release_year);
CREATE INDEX idx_movies_tmdb ON movies (tmdb_id);