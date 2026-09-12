package com.cinestats.backend_java.dto.request;

import jakarta.validation.Valid;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotEmpty;
import jakarta.validation.constraints.NotNull;
import java.math.BigDecimal;
import java.time.LocalDate;
import java.util.List;

public record LetterboxdImportRequest(
    @NotBlank(message = "Username is required")
    String username,

    @NotEmpty(message = "Entries list cannot be empty")
    @Valid
    List<DiaryEntry> entries
) {
    public record DiaryEntry(
        @NotBlank(message = "Movie title is required")
        String title,

        @NotNull(message = "Release year is required")
        Short releaseYear,

        LocalDate watchedDate,
        BigDecimal rating,
        Boolean isRewatch,
        String letterboxdUri
    ) {}
}