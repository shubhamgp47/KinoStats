import { useQuery } from "@tanstack/react-query";
import { apiClient } from "../../services/api";
import type {
  StatsOverviewResponse,
  GenreStatResponse,
  DirectorProgressResponse,
} from "../../types/api";

export function useStatsOverview() {
  return useQuery({
    queryKey: ["stats", "overview"],
    queryFn: async () => {
      const { data } = await apiClient.get<StatsOverviewResponse>(
        "/api/v1/stats/overview"
      );
      return data;
    },
  });
}

export function useGenreStats() {
  return useQuery({
    queryKey: ["stats", "genres"],
    queryFn: async () => {
      const { data } = await apiClient.get<GenreStatResponse[]>(
        "/api/v1/stats/genres"
      );
      return data;
    },
  });
}

export function useDirectorCompletionist(limit: number = 8) {
  return useQuery({
    queryKey: ["stats", "directors", limit],
    queryFn: async () => {
      const { data } = await apiClient.get<DirectorProgressResponse[]>(
        `/api/v1/stats/directors/completionist?limit=${limit}`
      );
      return data;
    },
  });
}