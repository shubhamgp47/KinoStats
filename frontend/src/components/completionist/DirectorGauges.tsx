import React from "react";
import { ExternalLink, Film } from "lucide-react";
import type { DirectorProgressResponse } from "../../types/api";

interface Props {
  directors: DirectorProgressResponse[];
}

export const DirectorGauges: React.FC<Props> = ({ directors }) => {
  return (
    <div className="bg-surface border border-border-zinc rounded-xl p-6 shadow-sm">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h2 className="text-lg font-bold text-zinc-100">
            Director Filmography Completion
          </h2>
          <p className="text-xs text-zinc-400 mt-0.5">
            Progress tracked against canonical feature films
          </p>
        </div>
        <Film className="w-5 h-5 text-accent" />
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {directors.map((director) => {
          const percentage = Math.round(director.completionPercentage);

          return (
            <div
              key={director.directorId}
              className="bg-zinc-900/50 border border-border-zinc/70 rounded-lg p-4 space-y-3 hover:border-zinc-700 transition-colors"
            >
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="font-semibold text-sm text-zinc-200">
                    {director.directorName}
                  </h3>
                  <p className="text-xs text-zinc-400">
                    {director.watchedCount} of {director.totalDirected} watched
                  </p>
                </div>
                <a
                  href={director.letterboxdUrl}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center gap-1 text-xs text-accent hover:underline font-medium"
                >
                  Letterboxd
                  <ExternalLink className="w-3 h-3" />
                </a>
              </div>

              {/* Progress Bar Container */}
              <div className="w-full bg-zinc-800 rounded-full h-2.5 overflow-hidden">
                <div
                  className="bg-accent h-2.5 rounded-full transition-all duration-500"
                  style={{ width: `${Math.min(percentage, 100)}%` }}
                />
              </div>

              <div className="flex justify-end">
                <span className="text-xs font-bold text-accent">
                  {percentage}%
                </span>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};