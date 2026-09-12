package com.cinestats.backend_java.dto.response;

public record GenreStatResponse(
    String genreName,
    long totalFilms,
    double averageRating,
    String letterboxdUrl
) {}