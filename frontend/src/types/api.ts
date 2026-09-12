export interface LetterboxdImportEntry {
  title: string;
  releaseYear: number;
  watchedDate: string;
  rating: number | null; // Allow null for unrated films
  isRewatch: boolean;
  letterboxdUri: string;
}

export interface LetterboxdImportRequest {
  username: string;
  entries: LetterboxdImportEntry[];
}

export interface ImportResponse {
  totalReceived: number;
  matchedInCache: number;
  queuedForEnrichment: number;
  userId: string;
  sessionToken: string;
}

export interface StatsOverviewResponse {
  totalWatched: number;
  totalHours: number;
  averageRating: number;
  mostWatchedYear: number;
  topDecade: string;
}

export interface GenreStatResponse {
  genreName: string;
  totalFilms: number;
  averageScore: number;
  letterboxdUrl: string;
}

export interface DirectorProgressResponse {
  directorId: number;
  directorName: string;
  slug: string;
  totalDirected: number;
  watchedCount: number;
  completionPercentage: number;
  letterboxdUrl: string;
}