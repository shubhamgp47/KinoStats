package com.cinestats.backend_java.service;

import com.cinestats.backend_java.dto.tmdb.TmdbMovieDetails;
import com.cinestats.backend_java.dto.tmdb.TmdbSearchResponse;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;

import java.util.Optional;

import static org.junit.jupiter.api.Assertions.*;

@SpringBootTest
class TmdbServiceTest {

    @Autowired
    private TmdbService tmdbService;

    @Test
    void searchMovie_shouldReturnInception() {
        Optional<TmdbSearchResponse.TmdbMovieResult> result = 
            tmdbService.searchMovie("Inception", (short) 2010);

        assertTrue(result.isPresent(), "Inception (2010) should be found on TMDB");
        assertEquals("Inception", result.get().title());
    }

    @Test
    void getMovieDetails_shouldReturnRuntimeAndDirector() {
        // TMDB ID for Inception is 27205
        Optional<TmdbMovieDetails> details = tmdbService.getMovieDetails(27205);

        assertTrue(details.isPresent(), "Movie details should be returned");
        assertEquals(148, details.get().runtimeMinutes(), "Inception runtime should be 148 minutes");
        
        boolean hasNolan = details.get().credits().crew().stream()
            .anyMatch(c -> "Director".equals(c.job()) && "Christopher Nolan".equals(c.name()));
        assertTrue(hasNolan, "Christopher Nolan should be listed as Director");
    }
}