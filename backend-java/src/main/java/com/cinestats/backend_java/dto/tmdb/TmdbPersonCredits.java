package com.cinestats.backend_java.dto.tmdb;

import java.util.List;

public record TmdbPersonCredits(
    List<TmdbCrewCredit> crew
) {
    public record TmdbCrewCredit(
        int id,
        String title,
        String department,
        String job
    ) {}
}