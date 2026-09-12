package com.cinestats.backend_java.model;

import jakarta.persistence.*;
import lombok.*;
import org.hibernate.annotations.CreationTimestamp;

import java.math.BigDecimal;
import java.time.Instant;
import java.time.LocalDate;

@Entity
@Table(
    name = "watch_logs",
    uniqueConstraints = {
        @UniqueConstraint(name = "uq_user_movie_watch", columnNames = {"user_id", "movie_id", "watched_date"})
    }
)
@Getter
@Setter
@NoArgsConstructor
@AllArgsConstructor
@Builder
public class WatchLog {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @ManyToOne(fetch = FetchType.LAZY, optional = false)
    @JoinColumn(name = "user_id", nullable = false)
    private User user;

    @ManyToOne(fetch = FetchType.LAZY, optional = false)
    @JoinColumn(name = "movie_id", nullable = false)
    private Movie movie;

    @Column(name = "watched_date")
    private LocalDate watchedDate;

    @Column(name = "rating", precision = 2, scale = 1, nullable = true)
    private BigDecimal rating;

    @Column(name = "is_rewatch", nullable = false)
    @Builder.Default
    private Boolean isRewatch = false;

    @Column(name = "letterboxd_uri", length = 512)
    private String letterboxdUri;

    @CreationTimestamp
    @Column(name = "created_at", nullable = false, updatable = false)
    private Instant createdAt;
}