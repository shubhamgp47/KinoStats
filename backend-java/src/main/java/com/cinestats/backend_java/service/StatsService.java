package com.cinestats.backend_java.service;

import com.cinestats.backend_java.dto.response.DirectorProgressResponse;
import com.cinestats.backend_java.dto.response.GenreStatResponse;
import com.cinestats.backend_java.dto.response.StatsOverviewResponse;
import com.cinestats.backend_java.model.User;
import com.cinestats.backend_java.repository.UserRepository;
import com.cinestats.backend_java.repository.WatchLogRepository;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Service;
import org.springframework.web.server.ResponseStatusException;

import java.util.List;

@Service
public class StatsService {

    private final WatchLogRepository watchLogRepository;
    private final UserRepository userRepository;

    public StatsService(WatchLogRepository watchLogRepository, UserRepository userRepository) {
        this.watchLogRepository = watchLogRepository;
        this.userRepository = userRepository;
    }

    public StatsOverviewResponse getOverview(String sessionToken) {
        User user = resolveUser(sessionToken);
        var stats = watchLogRepository.getOverviewStats(user.getId());
        if (stats == null) {
            return new StatsOverviewResponse(0, 0.0, 0.0, null, null);
        }
        return new StatsOverviewResponse(
            stats.getTotalWatched(),
            stats.getTotalHours(),
            stats.getAverageRating(),
            stats.getMostWatchedYear(),
            stats.getTopDecade()
        );
    }

    public List<GenreStatResponse> getGenreStats(String sessionToken) {
        User user = resolveUser(sessionToken);
        String username = user.getLetterboxdUsername();

        return watchLogRepository.getGenreStats(user.getId()).stream()
            .map(p -> {
                String slug = p.getGenreName().toLowerCase().replace(" ", "-");
                String letterboxdUrl = "https://letterboxd.com/" + username + "/films/genre/" + slug + "/";
                return new GenreStatResponse(p.getGenreName(), p.getTotalFilms(), p.getAverageRating(), letterboxdUrl);
            })
            .toList();
    }

    public List<DirectorProgressResponse> getDirectorStats(String sessionToken, int limit) {
        User user = resolveUser(sessionToken);
        String username = user.getLetterboxdUsername();

        return watchLogRepository.getTopDirectors(user.getId(), limit).stream()
            .map(d -> {
                long total = Math.max(d.getTotalDirected(), d.getWatchedCount());
                double percentage = total == 0 ? 0.0 : Math.round(((double) d.getWatchedCount() / total * 100.0) * 10.0) / 10.0;
                String slug = d.getDirectorName().toLowerCase().replaceAll("[^a-z0-9]+", "-");
                String url = "https://letterboxd.com/" + username + "/films/with/director/" + slug + "/";

                return new DirectorProgressResponse(
                    d.getDirectorId(),
                    d.getDirectorName(),
                    slug,
                    total,
                    d.getWatchedCount(),
                    percentage,
                    url
                );
            })
            .toList();
    }

    private User resolveUser(String sessionToken) {
        if (sessionToken == null || sessionToken.isBlank()) {
            throw new ResponseStatusException(HttpStatus.UNAUTHORIZED, "Missing X-Session-ID header");
        }
        return userRepository.findBySessionToken(sessionToken)
            .orElseThrow(() -> new ResponseStatusException(HttpStatus.NOT_FOUND, "User session not found"));
    }
}