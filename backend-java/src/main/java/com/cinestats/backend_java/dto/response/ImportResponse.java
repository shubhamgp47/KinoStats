package com.cinestats.backend_java.dto.response;

import java.util.UUID;

public record ImportResponse(
    int totalReceived,
    int matchedInCache,
    int queuedForEnrichment,
    UUID userId,
    String sessionToken
) {}