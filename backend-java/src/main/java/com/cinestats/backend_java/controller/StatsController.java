package com.cinestats.backend_java.controller;

import com.cinestats.backend_java.dto.response.DirectorProgressResponse;
import com.cinestats.backend_java.dto.response.GenreStatResponse;
import com.cinestats.backend_java.dto.response.StatsOverviewResponse;
import com.cinestats.backend_java.service.StatsService;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.List;

@RestController
@RequestMapping("/api/v1/stats")
@CrossOrigin(origins = "*")
public class StatsController {

    private final StatsService statsService;

    public StatsController(StatsService statsService) {
        this.statsService = statsService;
    }

    @GetMapping("/overview")
    public ResponseEntity<StatsOverviewResponse> getOverview(
            @RequestHeader("X-Session-ID") String sessionToken) {
        return ResponseEntity.ok(statsService.getOverview(sessionToken));
    }

    @GetMapping("/genres")
    public ResponseEntity<List<GenreStatResponse>> getGenres(
            @RequestHeader("X-Session-ID") String sessionToken) {
        return ResponseEntity.ok(statsService.getGenreStats(sessionToken));
    }

    @GetMapping("/directors/completionist")
    public ResponseEntity<List<DirectorProgressResponse>> getDirectors(
            @RequestHeader("X-Session-ID") String sessionToken,
            @RequestParam(defaultValue = "10") int limit) {
        return ResponseEntity.ok(statsService.getDirectorStats(sessionToken, limit));
    }
}