package com.cinestats.backend_java.model;

import jakarta.persistence.*;
import lombok.*;

@Entity
@Table(name = "genres")
@Getter
@Setter
@NoArgsConstructor
@AllArgsConstructor
@Builder
public class Genre {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Short id;

    @Column(name = "tmdb_genre_id", nullable = false, unique = true)
    private Integer tmdbGenreId;

    @Column(name = "name", nullable = false, unique = true, length = 50)
    private String name;
}