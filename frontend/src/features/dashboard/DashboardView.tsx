import React from "react";
import { Film, Clock, Star, Calendar, RefreshCw } from "lucide-react";
import {
  useStatsOverview,
  useGenreStats,
  useDirectorCompletionist,
} from "./useStats";
import { MetricCard } from "../../components/common/MetricCard";
import { GenreChart } from "../../components/charts/GenreChart";
import { DirectorGauges } from "../../components/completionist/DirectorGauges";

interface Props {
  onReset: () => void;
}

export const DashboardView: React.FC<Props> = ({ onReset }) => {
  const { data: overview, isLoading: loadingOverview } = useStatsOverview();
  const { data: genres, isLoading: loadingGenres } = useGenreStats();
  const { data: directors, isLoading: loadingDirectors } = useDirectorCompletionist(8);

  const isLoading = loadingOverview || loadingGenres || loadingDirectors;

  if (isLoading) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[50vh] space-y-3">
        <RefreshCw className="w-8 h-8 text-accent animate-spin" />
        <p className="text-sm text-zinc-400 font-medium">
          Aggregating your cinema statistics...
        </p>
      </div>
    );
  }

  return (
    <div className="w-full max-w-6xl space-y-8 animate-in fade-in duration-300">
      {/* Top Action Bar */}
      <div className="flex items-center justify-between">
        <h2 className="text-xl font-bold tracking-tight text-zinc-100">
          Letterboxd Overview
        </h2>
        <button
          onClick={onReset}
          className="text-xs text-zinc-400 hover:text-accent border border-border-zinc hover:border-accent/40 bg-surface px-3 py-1.5 rounded-lg transition-colors"
        >
          Upload New Export
        </button>
      </div>

      {/* KPI Cards Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <MetricCard
          label="Total Films"
          value={overview?.totalWatched ?? 0}
          icon={Film}
        />
        <MetricCard
          label="Time Watched"
          value={overview?.totalHours ? Math.round(overview.totalHours) : 0}
          subValue="hours"
          icon={Clock}
        />
        <MetricCard
          label="Average Rating"
          value={overview?.averageRating ? overview.averageRating.toFixed(2) : "N/A"}
          subValue="/ 5.0"
          icon={Star}
        />
        <MetricCard
          label="Peak Decade"
          value={overview?.topDecade ?? "N/A"}
          subValue={`Top Year: ${overview?.mostWatchedYear ?? "-"}`}
          icon={Calendar}
        />
      </div>

      {/* Charts & Completion Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        <div className="lg:col-span-1">
          {genres && <GenreChart genres={genres} />}
        </div>
        <div className="lg:col-span-2">
          {directors && <DirectorGauges directors={directors} />}
        </div>
      </div>
    </div>
  );
};