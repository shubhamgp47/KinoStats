package com.cinestats.backend_java.dto.response;
//Powers the completionist progress gauges
public record DirectorProgressResponse(
    Long directorId,
    String directorName,
    String slug,
    long totalDirected,
    long watchedCount,
    double completionPercentage,
    String letterboxdUrl
) {}