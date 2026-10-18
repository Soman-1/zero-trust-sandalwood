import React from 'react';
import { LucideIcon } from 'lucide-react';

interface StatCardProps {
  title: string;
  value: string | number;
  subtitle?: string;
  icon: LucideIcon;
  accentColor?: 'emerald' | 'cyan' | 'purple' | 'amber' | 'blue';
  glowColor?: string;
  trend?: {
    value: string;
    isPositive?: boolean;
  };
  onClick?: () => void;
}

export const StatCard: React.FC<StatCardProps> = ({
  title,
  value,
  subtitle,
  icon: Icon,
  accentColor = 'emerald',
  trend,
  onClick,
}) => {
  const colorMap = {
    emerald: {
      bg: 'bg-emerald-500/10',
      border: 'border-emerald-500/20',
      text: 'text-emerald-400',
      glow: 'group-hover:border-emerald-500/50 group-hover:shadow-glow-emerald',
      dot: 'bg-emerald-400',
    },
    cyan: {
      bg: 'bg-cyan-500/10',
      border: 'border-cyan-500/20',
      text: 'text-cyan-400',
      glow: 'group-hover:border-cyan-500/50 group-hover:shadow-glow-cyan',
      dot: 'bg-cyan-400',
    },
    purple: {
      bg: 'bg-purple-500/10',
      border: 'border-purple-500/20',
      text: 'text-purple-400',
      glow: 'group-hover:border-purple-500/50',
      dot: 'bg-purple-400',
    },
    amber: {
      bg: 'bg-amber-500/10',
      border: 'border-amber-500/20',
      text: 'text-amber-400',
      glow: 'group-hover:border-amber-500/50 group-hover:shadow-glow-amber',
      dot: 'bg-amber-400',
    },
    blue: {
      bg: 'bg-blue-500/10',
      border: 'border-blue-500/20',
      text: 'text-blue-400',
      glow: 'group-hover:border-blue-500/50',
      dot: 'bg-blue-400',
    },
  };

  const scheme = colorMap[accentColor] || colorMap.emerald;

  return (
    <div
      onClick={onClick}
      className={`glass-panel p-5 rounded-2xl transition-all duration-300 group border border-slate-800/80 relative overflow-hidden ${scheme.glow} ${
        onClick ? 'cursor-pointer active:scale-[0.99]' : ''
      }`}
    >
      {/* Ambient background light on hover */}
      <div className="absolute -top-12 -right-12 w-28 h-28 rounded-full bg-gradient-to-br from-white/5 to-transparent blur-xl pointer-events-none group-hover:opacity-100 opacity-30 transition-opacity"></div>

      <div className="flex items-start justify-between relative z-10">
        <div className="space-y-1.5">
          <div className="flex items-center gap-1.5">
            <span className={`w-1.5 h-1.5 rounded-full ${scheme.dot} animate-pulse`}></span>
            <p className="text-[11px] font-semibold uppercase tracking-wider text-slate-400 font-mono">
              {title}
            </p>
          </div>
          <h3 className="text-2xl lg:text-3xl font-bold text-slate-50 font-mono tracking-tight">
            {typeof value === 'number' ? value.toLocaleString() : value}
          </h3>
          {subtitle && <p className="text-xs text-slate-400 font-medium">{subtitle}</p>}
          {trend && (
            <div className="flex items-center gap-1.5 pt-0.5 text-xs font-mono">
              <span className={`font-semibold ${trend.isPositive ? 'text-emerald-400' : 'text-slate-400'}`}>
                {trend.value}
              </span>
              <span className="text-slate-500 text-[10px]">vs previous cycle</span>
            </div>
          )}
        </div>

        <div className={`p-3 rounded-xl ${scheme.bg} ${scheme.border} ${scheme.text} border transition-transform duration-300 group-hover:scale-110 shadow-sm`}>
          <Icon className="w-5 h-5" />
        </div>
      </div>
    </div>
  );
};
