import React from "react";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  Cell,
} from "recharts";
import type { GenreStatResponse } from "../../types/api";

interface Props {
  genres: GenreStatResponse[];
}

export const GenreChart: React.FC<Props> = ({ genres }) => {
  const data = [...genres]
    .sort((a, b) => b.totalFilms - a.totalFilms)
    .slice(0, 8);

  return (
    <div className="bg-surface border border-border-zinc rounded-xl p-6 shadow-sm">
      <h2 className="text-lg font-bold text-zinc-100 mb-1">Top Genres</h2>
      <p className="text-xs text-zinc-400 mb-6">
        Distribution by volume of watched catalog
      </p>

      <div className="h-64 w-full">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={data} layout="vertical" margin={{ left: 10, right: 20 }}>
            <XAxis type="number" stroke="#71717a" fontSize={12} tickLine={false} />
            <YAxis
              type="category"
              dataKey="genreName"
              stroke="#a1a1aa"
              fontSize={12}
              tickLine={false}
              axisLine={false}
              width={90}
            />
            <Tooltip
              contentStyle={{
                backgroundColor: "#18181b",
                borderColor: "#27272a",
                borderRadius: "8px",
                color: "#f4f4f5",
                fontSize: "12px",
              }}
              formatter={(val: unknown) => [`${Number(val ?? 0)} films`, "Watched"]}
            />
            <Bar dataKey="totalFilms" radius={[0, 4, 4, 0]}>
              {data.map((_, index) => (
                <Cell
                  key={`cell-${index}`}
                  fill={index === 0 ? "#00e054" : "#27272a"}
                  className="hover:opacity-80 transition-opacity"
                />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
};