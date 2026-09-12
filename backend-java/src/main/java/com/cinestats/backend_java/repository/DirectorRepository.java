package com.cinestats.backend_java.repository;

import com.cinestats.backend_java.model.Director;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.util.Optional;

@Repository
public interface DirectorRepository extends JpaRepository<Director, Long> {
    Optional<Director> findByTmdbPersonId(Integer tmdbPersonId);
}