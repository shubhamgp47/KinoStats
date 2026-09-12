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

import java.time.Instant;
import java.util.*;
import java.util.concurrent.*;
import java.math.BigDecimal;

@Service
public class IngestionService {

    private static final Logger log = LoggerFactory.getLogger(IngestionService.class);

    private final UserRepository userRepository;
    private final MovieRepository movieRepository;
    private final WatchLogRepository watchLogRepository;
    private final GenreRepository genreRepository;
    private final DirectorRepository directorRepository;
    private final TmdbService tmdbService;

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
        User user = resolveOrCreateUser(request.username(), sessionToken);

        List<LetterboxdImportRequest.DiaryEntry> entries = request.entries();
        int totalReceived = entries.size();
        int matchedInCache = 0;
        int enrichedCount = 0;

        List<LetterboxdImportRequest.DiaryEntry> cacheMisses = new ArrayList<>();
        Map<String, Movie> resolvedMovies = new ConcurrentHashMap<>();

        // Step 1: Query Local Postgres Cache
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

        // Step 2: Concurrently Resolve Cache Misses via TMDB using Java 21 Virtual Threads
        if (!cacheMisses.isEmpty()) {
            enrichedCount = resolveMissesConcurrently(cacheMisses, resolvedMovies);
        }

        // Step 3: Persist Watch Logs for resolved movies
        persistWatchLogs(user, entries, resolvedMovies);

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

        // Use Java 21 Virtual Thread Per Task Executor
        try (var executor = Executors.newVirtualThreadPerTaskExecutor()) {
            List<Callable<Void>> tasks = misses.stream().map(entry -> (Callable<Void>) () -> {
                String cacheKey = (entry.title() + "_" + entry.releaseYear()).toLowerCase();
                
                // Avoid redundant TMDB calls if duplicate movies exist in the same import file
                if (resolvedMovies.containsKey(cacheKey)) {
                    return null;
                }

                tmdbService.searchMovie(entry.title(), entry.releaseYear()).ifPresent(searchResult -> {
                    Optional<TmdbMovieDetails> detailsOpt = tmdbService.getMovieDetails(searchResult.id());
                    if (detailsOpt.isPresent()) {
                        Movie savedMovie = persistEnrichedMovie(detailsOpt.get(), entry.releaseYear());
                        resolvedMovies.put(cacheKey, savedMovie);
                    } else {
                        log.warn("Could not fetch TMDB details for '{}' (ID: {})", entry.title(), searchResult.id());
                    }
                });
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
                Genre genre = genreRepository.findByTmdbGenreId(g.id())
                        .orElseGet(() -> genreRepository.save(
                                Genre.builder()
                                        .tmdbGenreId(g.id())
                                        .name(g.name())
                                        .build()
                        ));
                genres.add(genre);
            }
        }

        Set<Director> directors = new HashSet<>();
        if (details.credits() != null && details.credits().crew() != null) {
            details.credits().crew().stream()
                    .filter(c -> "Director".equalsIgnoreCase(c.job()))
                    .forEach(c -> {
                        Director director = directorRepository.findByTmdbPersonId(c.id())
                                .orElseGet(() -> directorRepository.save(
                                        Director.builder()
                                                .tmdbPersonId(c.id())
                                                .name(c.name())
                                                .profilePath(c.profilePath())
                                                .build()
                                ));
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

        return movieRepository.save(movie);
    }

    private void persistWatchLogs(
            User user,
            List<LetterboxdImportRequest.DiaryEntry> entries,
            Map<String, Movie> resolvedMovies) {

        List<WatchLog> batchToSave = new ArrayList<>();
        // In-memory set to prevent duplicate entries inside the current batch
        Set<String> processedKeysInBatch = new HashSet<>();

        for (var entry : entries) {
            String cacheKey = (entry.title() + "_" + entry.releaseYear()).toLowerCase();
            Movie movie = resolvedMovies.get(cacheKey);

            if (movie != null) {
                // Compound deduplication key: movie_id + watched_date
                String uniqueWatchKey = movie.getId() + "_" + entry.watchedDate();

                // 1. Skip if duplicate exists inside this incoming batch
                if (processedKeysInBatch.contains(uniqueWatchKey)) {
                    continue;
                }

                // 2. Skip if duplicate already exists committed in PostgreSQL
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