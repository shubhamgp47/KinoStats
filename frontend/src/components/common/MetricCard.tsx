import React from "react";
import type { LucideIcon } from "lucide-react";

interface MetricCardProps {
  label: string;
  value: string | number;
  subValue?: string;
  icon: LucideIcon;
}

export const MetricCard: React.FC<MetricCardProps> = ({
  label,
  value,
  subValue,
  icon: Icon,
}) => {
  return (
    <div className="bg-surface border border-border-zinc rounded-xl p-5 shadow-sm hover:border-zinc-700 transition-colors">
      <div className="flex items-center justify-between">
        <span className="text-xs font-semibold uppercase tracking-wider text-zinc-400">
          {label}
        </span>
        <div className="p-2 rounded-lg bg-zinc-900 border border-border-zinc text-accent">
          <Icon className="w-4 h-4" />
        </div>
      </div>
      <div className="mt-3 flex items-baseline gap-2">
        <span className="text-3xl font-black tracking-tight text-zinc-100">
          {value}
        </span>
        {subValue && (
          <span className="text-xs text-zinc-400 font-medium">{subValue}</span>
        )}
      </div>
    </div>
  );
};