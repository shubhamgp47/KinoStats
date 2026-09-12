package com.cinestats.backend_java.model;

import jakarta.persistence.*;
import lombok.*;

@Entity
@Table(name = "directors")
@Getter
@Setter
@NoArgsConstructor
@AllArgsConstructor
@Builder
public class Director {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(name = "tmdb_person_id", nullable = false, unique = true)
    private Integer tmdbPersonId;

    @Column(name = "name", nullable = false, length = 150)
    private String name;

    @Column(name = "profile_path", length = 255)
    private String profilePath;
}