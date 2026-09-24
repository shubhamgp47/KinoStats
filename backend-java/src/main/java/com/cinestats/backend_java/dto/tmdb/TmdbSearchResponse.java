package com.cinestats.backend_java.dto.tmdb;

import com.fasterxml.jackson.annotation.JsonProperty;
import java.util.List;

public record TmdbSearchResponse(
    int page,
    List<TmdbMovieResult> results,
    @JsonProperty("total_results") int totalResults // Bridges external TMDB snake_case keys directly to idiomatic Java camelCase fields.
) {
    public record TmdbMovieResult(
        int id,
        String title,
        @JsonProperty("release_date") String releaseDate,
        @JsonProperty("poster_path") String posterPath,
        @JsonProperty("backdrop_path") String backdropPath,
        String overview
    ) {}
}