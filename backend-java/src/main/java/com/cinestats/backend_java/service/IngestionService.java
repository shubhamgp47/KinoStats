package com.cinestats.backend_java.service;

import com.cinestats.backend_java.dto.request.LetterboxdImportRequest;
import com.cinestats.backend_java.dto.response.ImportResponse;
import com.cinestats.backend_java.dto.tmdb.TmdbMovieDetails;
import com.cinestats.backend_java.model.*;
import com.cinestats.backend_java.repository.*;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.math.BigDecimal;
import java.time.Instant;
import java.util.*;
import java.util.concurrent.*;

@Service
public class IngestionService {

    private static final Logger log = LoggerFactory.getLogger(IngestionService.class);

    private final UserRepository userRepository;
    private final MovieRepository movieRepository;
    private final WatchLogRepository watchLogRepository;
    private final GenreRepository genreRepository;
    private final DirectorRepository directorRepository;
    private final TmdbService tmdbService;

    // Concurrent caches to prevent duplicate DB calls & race condition collisions
    private final Map<Integer, Director> directorCache = new ConcurrentHashMap<>();
    private final Map<Integer, Genre> genreCache = new ConcurrentHashMap<>();

    public IngestionService(
            UserRepository userRepository,
            MovieRepository movieRepository,
            WatchLogRepository watchLogRepository,
            GenreRepository genreRepository,
            DirectorRepository directorRepository,
            TmdbService tmdbService) {
        this.userRepository = userRepository;
        this.movieRepository = movieRepository;
        this.watchLogRepository = watchLogRepository;
        this.genreRepository = genreRepository;
        this.directorRepository = directorRepository;
        this.tmdbService = tmdbService;
    }

    public ImportResponse processImport(LetterboxdImportRequest request, String sessionToken) {
        log.info("Starting Letterboxd import for user: '{}' with {} total entries", 
                request.username(), request.entries().size());

        User user = resolveOrCreateUser(request.username(), sessionToken);
        List<LetterboxdImportRequest.DiaryEntry> entries = request.entries();
        int totalReceived = entries.size();
        int matchedInCache = 0;
        int enrichedCount = 0;

        List<LetterboxdImportRequest.DiaryEntry> cacheMisses = new ArrayList<>();
        Map<String, Movie> resolvedMovies = new ConcurrentHashMap<>();

        // Step 1: Local Postgres Cache Check
        for (LetterboxdImportRequest.DiaryEntry entry : entries) {
            String cacheKey = (entry.title() + "_" + entry.releaseYear()).toLowerCase();
            Optional<Movie> cached = movieRepository.findByTitleIgnoreCaseAndReleaseYear(entry.title(), entry.releaseYear());
            if (cached.isPresent()) {
                matchedInCache++;
                resolvedMovies.put(cacheKey, cached.get());
            } else {
                cacheMisses.add(entry);
            }
        }

        log.info("Local Cache Lookup Complete: {} hits, {} misses to fetch from TMDB", 
                matchedInCache, cacheMisses.size());

        // Step 2: TMDB Resolution for misses
        if (!cacheMisses.isEmpty()) {
            log.info("Resolving {} cache misses concurrently via Virtual Threads...", cacheMisses.size());
            enrichedCount = resolveMissesConcurrently(cacheMisses, resolvedMovies);
        }

        // Step 3: Watch Logs Persistence
        log.info("Persisting watch logs for {} resolved movies...", resolvedMovies.size());
        persistWatchLogs(user, entries, resolvedMovies);
        log.info("Watch logs successfully persisted for user '{}'", user.getLetterboxdUsername());

        return new ImportResponse(
                totalReceived,
                matchedInCache,
                enrichedCount,
                user.getId(),
                user.getSessionToken()
        );
    }

    private User resolveOrCreateUser(String username, String sessionToken) {
        if (sessionToken != null && !sessionToken.isBlank()) {
            Optional<User> existingSessionUser = userRepository.findBySessionToken(sessionToken);
            if (existingSessionUser.isPresent()) {
                User u = existingSessionUser.get();
                u.setLastActiveAt(Instant.now());
                return userRepository.save(u);
            }
        }
        return userRepository.findByLetterboxdUsername(username)
                .orElseGet(() -> userRepository.save(
                        User.builder()
                                .letterboxdUsername(username)
                                .sessionToken(UUID.randomUUID().toString())
                                .isGuest(true)
                                .lastActiveAt(Instant.now())
                                .build()
                ));
    }

    private int resolveMissesConcurrently(
            List<LetterboxdImportRequest.DiaryEntry> misses,
            Map<String, Movie> resolvedMovies) {

        java.util.concurrent.atomic.AtomicInteger completed = new java.util.concurrent.atomic.AtomicInteger(0);
        int total = misses.size();

        try (var executor = Executors.newVirtualThreadPerTaskExecutor()) {
            List<Callable<Void>> tasks = misses.stream().map(entry -> (Callable<Void>) () -> {
                String cacheKey = (entry.title() + "_" + entry.releaseYear()).toLowerCase();

                if (resolvedMovies.containsKey(cacheKey)) {
                    return null;
                }

                tmdbService.searchMovie(entry.title(), entry.releaseYear()).ifPresent(searchResult -> {
                    Optional<TmdbMovieDetails> detailsOpt = tmdbService.getMovieDetails(searchResult.id());
                    if (detailsOpt.isPresent()) {
                        Movie savedMovie = persistEnrichedMovie(detailsOpt.get(), entry.releaseYear());
                        if (savedMovie != null) {
                            resolvedMovies.put(cacheKey, savedMovie);
                        }
                    } else {
                        log.warn("Could not fetch TMDB details for '{}' (ID: {})", entry.title(), searchResult.id());
                    }
                });

                int current = completed.incrementAndGet();
                if (current % 25 == 0 || current == total) {
                    log.info("Ingestion Progress: [{}/{}] movies resolved from TMDB", current, total);
                }
                return null;
            }).toList();

            executor.invokeAll(tasks);
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
            log.error("Virtual thread enrichment tasks interrupted", e);
        }

        return resolvedMovies.size();
    }

    @Transactional
    public synchronized Movie persistEnrichedMovie(TmdbMovieDetails details, short releaseYear) {
        Optional<Movie> existing = movieRepository.findByTmdbId(details.id());
        if (existing.isPresent()) {
            return existing.get();
        }

        Set<Genre> genres = new HashSet<>();
        if (details.genres() != null) {
            for (var g : details.genres()) {
                Genre genre = genreCache.computeIfAbsent(g.id(), genreId ->
                    genreRepository.findByTmdbGenreId(genreId)
                        .orElseGet(() -> genreRepository.save(
                            Genre.builder()
                                .tmdbGenreId(g.id())
                                .name(g.name())
                                .build()
                        ))
                );
                genres.add(genre);
            }
        }

        Set<Director> directors = new HashSet<>();
        if (details.credits() != null && details.credits().crew() != null) {
            details.credits().crew().stream()
                    .filter(c -> "Director".equalsIgnoreCase(c.job()))
                    .forEach(c -> {
                        Director director = directorCache.computeIfAbsent(c.id(), personId ->
                            directorRepository.findByTmdbPersonId(personId)
                                .orElseGet(() -> {
                                    log.info("Fetching canon film count for director: {} (ID: {})", c.name(), c.id());
                                    int totalCanon = tmdbService.getDirectorFeatureFilmCount(c.id());
                                    return directorRepository.save(
                                        Director.builder()
                                                .tmdbPersonId(c.id())
                                                .name(c.name())
                                                .profilePath(c.profilePath())
                                                .totalDirected(totalCanon > 0 ? totalCanon : 1)
                                                .build()
                                    );
                                })
                        );
                        directors.add(director);
                    });
        }

        Movie movie = Movie.builder()
                .tmdbId(details.id())
                .title(details.title())
                .releaseYear(releaseYear)
                .runtimeMinutes(details.runtimeMinutes() != null ? details.runtimeMinutes().shortValue() : (short) 0)
                .posterPath(details.posterPath())
                .backdropPath(details.backdropPath())
                .overview(details.overview())
                .genres(genres)
                .directors(directors)
                .build();

        try {
            return movieRepository.save(movie);
        } catch (Exception e) {
            // If another virtual thread already saved this exact movie, return the cached record
            return movieRepository.findByTmdbId(details.id()).orElse(null);
        }
    }

    private void persistWatchLogs(
            User user,
            List<LetterboxdImportRequest.DiaryEntry> entries,
            Map<String, Movie> resolvedMovies) {

        List<WatchLog> batchToSave = new ArrayList<>();
        Set<String> processedKeysInBatch = new HashSet<>();

        for (var entry : entries) {
            String cacheKey = (entry.title() + "_" + entry.releaseYear()).toLowerCase();
            Movie movie = resolvedMovies.get(cacheKey);

            if (movie != null) {
                String uniqueWatchKey = movie.getId() + "_" + entry.watchedDate();

                if (processedKeysInBatch.contains(uniqueWatchKey)) {
                    continue;
                }

                boolean alreadyLogged = watchLogRepository.existsByUserIdAndMovieIdAndWatchedDate(
                        user.getId(), movie.getId(), entry.watchedDate());

                if (!alreadyLogged) {
                    BigDecimal cleanRating = (entry.rating() != null && entry.rating().doubleValue() > 0.0)
                            ? entry.rating()
                            : null;

                    batchToSave.add(WatchLog.builder()
                            .user(user)
                            .movie(movie)
                            .watchedDate(entry.watchedDate())
                            .rating(cleanRating)
                            .isRewatch(Boolean.TRUE.equals(entry.isRewatch()))
                            .letterboxdUri(entry.letterboxdUri())
                            .build());

                    processedKeysInBatch.add(uniqueWatchKey);
                }
            }
        }

        if (!batchToSave.isEmpty()) {
            watchLogRepository.saveAll(batchToSave);
        }
    }
}