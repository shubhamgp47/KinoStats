package com.cinestats.backend_java.repository;

import com.cinestats.backend_java.model.WatchLog;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import org.springframework.stereotype.Repository;

import java.time.LocalDate;
import java.util.List;
import java.util.Optional;
import java.util.UUID;

@Repository
public interface WatchLogRepository extends JpaRepository<WatchLog, Long> {

    boolean existsByUserIdAndMovieIdAndWatchedDate(UUID userId, Long movieId, LocalDate watchedDate);

    // 1. Overview aggregates
    @Query(value = """
        SELECT 
            COUNT(wl.id) AS totalWatched,
            COALESCE(ROUND(SUM(m.runtime_minutes)::numeric / 60.0, 1), 0.0) AS totalHours,
            COALESCE(ROUND(AVG(wl.rating), 2), 0.0) AS averageRating,
            (
                SELECT EXTRACT(YEAR FROM wl_sub.watched_date)::integer
                FROM watch_logs wl_sub
                WHERE wl_sub.user_id = :userId AND wl_sub.watched_date IS NOT NULL
                GROUP BY EXTRACT(YEAR FROM wl_sub.watched_date)
                ORDER BY COUNT(*) DESC
                LIMIT 1
            ) AS mostWatchedYear,
            (
                SELECT (FLOOR(m_sub.release_year / 10) * 10)::text || 's'
                FROM watch_logs wl_sub2
                JOIN movies m_sub ON wl_sub2.movie_id = m_sub.id
                WHERE wl_sub2.user_id = :userId
                GROUP BY FLOOR(m_sub.release_year / 10)
                ORDER BY COUNT(*) DESC
                LIMIT 1
            ) AS topDecade
        FROM watch_logs wl
        JOIN movies m ON wl.movie_id = m.id
        WHERE wl.user_id = :userId
    """, nativeQuery = true)
    OverviewProjection getOverviewStats(@Param("userId") UUID userId);

    interface OverviewProjection {
        long getTotalWatched();
        double getTotalHours();
        double getAverageRating();
        Integer getMostWatchedYear();
        String getTopDecade();
    }

    // 2. Genre Breakdown
    @Query(value = """
        SELECT 
            g.name AS genreName,
            COUNT(DISTINCT m.id) AS totalFilms,
            COALESCE(ROUND(AVG(wl.rating), 2), 0.0) AS averageRating
        FROM watch_logs wl
        JOIN movies m ON wl.movie_id = m.id
        JOIN movie_genres mg ON m.id = mg.movie_id
        JOIN genres g ON mg.genre_id = g.id
        WHERE wl.user_id = :userId
        GROUP BY g.name
        ORDER BY totalFilms DESC
    """, nativeQuery = true)
    List<GenreStatProjection> getGenreStats(@Param("userId") UUID userId);

    interface GenreStatProjection {
        String getGenreName();
        long getTotalFilms();
        double getAverageRating();
    }

    // 3. Director Completionist Breakdown
    @Query(value = """
        SELECT 
            d.id AS directorId,
            d.name AS directorName,
            LOWER(REPLACE(REPLACE(d.name, ' ', '-'), '.', '')) AS slug,
            GREATEST(COALESCE(d.total_directed, 0), COUNT(DISTINCT wl.movie_id)) AS totalDirected,
            COUNT(DISTINCT wl.movie_id) AS watchedCount,
            ROUND(
                (COUNT(DISTINCT wl.movie_id)::NUMERIC / 
                NULLIF(GREATEST(COALESCE(d.total_directed, 0), COUNT(DISTINCT wl.movie_id)), 0)
                ) * 100, 
                1
            ) AS completionPercentage
        FROM watch_logs wl
        JOIN movies m ON wl.movie_id = m.id
        JOIN movie_directors md ON m.id = md.movie_id
        JOIN directors d ON md.director_id = d.id
        WHERE wl.user_id = :userId
        GROUP BY d.id, d.name, d.total_directed
        ORDER BY watchedCount DESC
        LIMIT :limit
        """, nativeQuery = true)
    List<DirectorStatProjection> getTopDirectors(@Param("userId") UUID userId, @Param("limit") int limit);

    public interface DirectorStatProjection {
        Long getDirectorId();
        String getDirectorName();
        String getSlug();
        long getTotalDirected();
        long getWatchedCount();
        Double getCompletionPercentage();
    }
}