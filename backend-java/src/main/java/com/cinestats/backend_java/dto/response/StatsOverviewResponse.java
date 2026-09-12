package com.cinestats.backend_java.dto.response;

public record StatsOverviewResponse(
    long totalWatched,
    double totalHours,
    double averageRating,
    Integer mostWatchedYear,
    String topDecade
) {}