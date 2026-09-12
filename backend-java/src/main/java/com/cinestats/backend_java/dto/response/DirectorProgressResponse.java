package com.cinestats.backend_java.dto.response;

public record DirectorProgressResponse(
    Long directorId,
    String directorName,
    String slug,
    long totalDirected,
    long watchedCount,
    double completionPercentage,
    String letterboxdUrl
) {}