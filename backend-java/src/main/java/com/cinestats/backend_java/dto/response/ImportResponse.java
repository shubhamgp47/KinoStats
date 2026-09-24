package com.cinestats.backend_java.dto.response;

import java.util.UUID;
 //Informs the user how many titles hit the database-first cache instantly 
 // versus how many required TMDB lookups, while provisioning or refreshing their guest session token.
public record ImportResponse(
    int totalReceived,
    int matchedInCache,
    int queuedForEnrichment,
    UUID userId,
    String sessionToken
) {}