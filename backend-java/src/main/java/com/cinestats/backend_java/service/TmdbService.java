package com.cinestats.backend_java.service;

import com.cinestats.backend_java.dto.tmdb.TmdbMovieDetails;
import com.cinestats.backend_java.dto.tmdb.TmdbSearchResponse;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.MediaType;
import org.springframework.stereotype.Service;
import org.springframework.web.client.RestClient;

import java.util.Optional;
import java.util.concurrent.Semaphore;

@Service
public class TmdbService {

    private static final Logger log = LoggerFactory.getLogger(TmdbService.class);
    private final RestClient restClient;

    // Allow at most 10 concurrent requests to TMDB across all virtual threads
    private final Semaphore rateLimiter = new Semaphore(10);

    public TmdbService(
        @Value("${tmdb.api-url}") String apiUrl,
        @Value("${tmdb.api-key}") String apiKey
    ) {
        this.restClient = RestClient.builder()
            .baseUrl(apiUrl)
            .defaultHeader("Authorization", "Bearer " + apiKey)
            .defaultHeader("Accept", MediaType.APPLICATION_JSON_VALUE)
            .build();
    }

    /**
     * Search TMDB for a movie by title and exact release year.
     */
    public Optional<TmdbSearchResponse.TmdbMovieResult> searchMovie(String title, short releaseYear) {
        try {
            rateLimiter.acquire();
            // Smooth out request bursts
            Thread.sleep(25);

            TmdbSearchResponse response = restClient.get()
                .uri(uriBuilder -> uriBuilder
                    .path("/search/movie")
                    .queryParam("query", title)
                    .queryParam("year", releaseYear)
                    .queryParam("include_adult", false)
                    .build())
                .retrieve()
                .body(TmdbSearchResponse.class);

            if (response != null && response.results() != null && !response.results().isEmpty()) {
                return Optional.of(response.results().getFirst());
            }
            return Optional.empty();
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
            log.warn("TMDB search thread interrupted for '{}'", title);
            return Optional.empty();
        } catch (Exception e) {
            log.error("Failed to query TMDB search for '{}' ({}): {}", title, releaseYear, e.getMessage());
            return Optional.empty();
        } finally {
            rateLimiter.release();
        }
    }

    /**
     * Fetch complete movie metadata including crew/directors in a single request
     * using TMDB's 'append_to_response=credits'.
     */
    public Optional<TmdbMovieDetails> getMovieDetails(int tmdbId) {
        try {
            rateLimiter.acquire();
            Thread.sleep(25);

            TmdbMovieDetails details = restClient.get()
                .uri(uriBuilder -> uriBuilder
                    .path("/movie/{id}")
                    .queryParam("append_to_response", "credits")
                    .build(tmdbId))
                .retrieve()
                .body(TmdbMovieDetails.class);

            return Optional.ofNullable(details);
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
            log.warn("TMDB details thread interrupted for ID {}", tmdbId);
            return Optional.empty();
        } catch (Exception e) {
            log.error("Failed to fetch TMDB details for ID {}: {}", tmdbId, e.getMessage());
            return Optional.empty();
        } finally {
            rateLimiter.release();
        }
    }
}