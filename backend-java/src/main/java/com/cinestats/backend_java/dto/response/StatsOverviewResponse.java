package com.cinestats.backend_java.dto.response;
//Aggregates diary activity into summary metrics, formatted cleanly for frontend display.
public record StatsOverviewResponse(
    long totalWatched,
    double totalHours,
    double averageRating,
    Integer mostWatchedYear,
    String topDecade
) {}