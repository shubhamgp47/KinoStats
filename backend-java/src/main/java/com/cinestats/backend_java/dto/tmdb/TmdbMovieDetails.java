package com.cinestats.backend_java.dto.tmdb;

import com.fasterxml.jackson.annotation.JsonProperty;
import java.util.List;

public record TmdbMovieDetails(
    int id,
    String title,
    @JsonProperty("runtime") Integer runtimeMinutes,
    @JsonProperty("poster_path") String posterPath,
    @JsonProperty("backdrop_path") String backdropPath,
    @JsonProperty("overview") String overview,
    List<TmdbGenre> genres,
    Credits credits
) {
    public record TmdbGenre(int id, String name) {}

    public record Credits(List<CrewMember> crew) {
        public record CrewMember(
            int id,
            String name,
            String job,
            @JsonProperty("profile_path") String profilePath
        ) {}
    }
}