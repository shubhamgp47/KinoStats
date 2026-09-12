package com.cinestats.backend_java.model;

import jakarta.persistence.*;
import lombok.*;
import org.hibernate.annotations.CreationTimestamp;
import org.hibernate.annotations.UpdateTimestamp;

import java.time.Instant;
import java.util.UUID;

@Entity
@Table(name = "users")
@Getter
@Setter
@NoArgsConstructor
@AllArgsConstructor
@Builder
public class User {

    @Id
    @GeneratedValue(strategy = GenerationType.UUID)
    private UUID id;

    @Column(name = "letterboxd_username", nullable = false, length = 100)
    private String letterboxdUsername;

    @Column(name = "session_token", unique = true)
    private String sessionToken;

    @Column(name = "is_guest", nullable = false)
    @Builder.Default
    private Boolean isGuest = true;

    @CreationTimestamp
    @Column(name = "created_at", nullable = false, updatable = false)
    private Instant createdAt;

    @UpdateTimestamp
    @Column(name = "last_active_at", nullable = false)
    private Instant lastActiveAt;
}