package com.cinestats.backend_java.controller;

import com.cinestats.backend_java.dto.request.LetterboxdImportRequest;
import com.cinestats.backend_java.dto.response.ImportResponse;
import com.cinestats.backend_java.service.IngestionService;
import jakarta.validation.Valid;
import org.springframework.http.HttpHeaders;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

@RestController
@RequestMapping("/api/v1/imports")
@CrossOrigin(origins = "*") // Allows local React frontend to call on port 5173
public class ImportController {

    private final IngestionService ingestionService;

    public ImportController(IngestionService ingestionService) {
        this.ingestionService = ingestionService;
    }

    @PostMapping("/letterboxd")
    public ResponseEntity<ImportResponse> importLetterboxd(
            @RequestHeader(value = "X-Session-ID", required = false) String sessionToken,
            @Valid @RequestBody LetterboxdImportRequest request) {

        ImportResponse response = ingestionService.processImport(request, sessionToken);

        HttpHeaders headers = new HttpHeaders();
        headers.set("X-Session-ID", response.sessionToken());

        return ResponseEntity.status(HttpStatus.ACCEPTED)
                .headers(headers)
                .body(response);
    }
}