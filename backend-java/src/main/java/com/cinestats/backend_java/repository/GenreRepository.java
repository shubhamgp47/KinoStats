package com.cinestats.backend_java.repository;

import com.cinestats.backend_java.model.Genre;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.util.Optional;

@Repository
public interface GenreRepository extends JpaRepository<Genre, Short> {
    Optional<Genre> findByTmdbGenreId(Integer tmdbGenreId);
    Optional<Genre> findByNameIgnoreCase(String name);
}