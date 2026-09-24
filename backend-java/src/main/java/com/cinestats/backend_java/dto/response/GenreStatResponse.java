package com.cinestats.backend_java.dto.response;
//Powers the genre distribution charts (pie/bar) in Recharts
public record GenreStatResponse(
    String genreName,
    long totalFilms,
    double averageRating,
    String letterboxdUrl
) {}