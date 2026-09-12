package com.cinestats.backend_java;

import com.cinestats.backend_java.dto.request.LetterboxdImportRequest;
import com.cinestats.backend_java.dto.response.ImportResponse;
import com.cinestats.backend_java.dto.response.StatsOverviewResponse;
import com.cinestats.backend_java.service.IngestionService;
import com.cinestats.backend_java.service.StatsService;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.test.context.ActiveProfiles;
import org.springframework.transaction.annotation.Transactional;

import java.math.BigDecimal;
import java.time.LocalDate;
import java.util.List;

import static org.junit.jupiter.api.Assertions.*;

@SpringBootTest
@ActiveProfiles("test")
@Transactional // Rolls back all database operations after the test completes
class ImportAndStatsIntegrationTest {

    @Autowired
    private IngestionService ingestionService;

    @Autowired
    private StatsService statsService;

    @Test
    @DisplayName("End-to-end flow: Ingest Letterboxd entry, persist cache, and calculate overview stats")
    void testFullIngestionAndAggregationPipeline() {
        var entry = new LetterboxdImportRequest.DiaryEntry(
                "Inception",
                (short) 2010,
                LocalDate.of(2024, 3, 15),
                new BigDecimal("4.5"),
                false,
                "https://boxd.it/1srW"
        );

        var request = new LetterboxdImportRequest("integration_tester", List.of(entry));

        // 1. Ingest entry
        ImportResponse importResponse = ingestionService.processImport(request, null);
        assertNotNull(importResponse.sessionToken());
        assertEquals(1, importResponse.totalReceived());

        // 2. Query stats engine using the session token
        StatsOverviewResponse stats = statsService.getOverview(importResponse.sessionToken());

        assertEquals(1, stats.totalWatched());
        assertEquals(2.5, stats.totalHours(), 0.1);
        assertEquals(4.5, stats.averageRating(), 0.01);
        assertEquals(2024, stats.mostWatchedYear());
        assertEquals("2010s", stats.topDecade());
    }
}