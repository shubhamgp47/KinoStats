package com.cinestats.backend_java.repository;

import com.cinestats.backend_java.model.Movie;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import org.springframework.stereotype.Repository;

import java.util.Optional;

@Repository
public interface MovieRepository extends JpaRepository<Movie, Long> {

    // Used for exact matching against our PostgreSQL cache
    Optional<Movie> findByTitleIgnoreCaseAndReleaseYear(String title, Short releaseYear); // SELECT * FROM movies WHERE LOWER(title) = LOWER(?) AND release_year = ?;

    // Fetch movie with genres and directors in one query (solves N+1 problem)
    @Query("""
        SELECT m FROM Movie m
        LEFT JOIN FETCH m.genres
        LEFT JOIN FETCH m.directors
        WHERE m.id = :id
    """)
    Optional<Movie> findByIdWithDetails(@Param("id") Long id);

    Optional<Movie> findByTmdbId(Integer tmdbId);
} 