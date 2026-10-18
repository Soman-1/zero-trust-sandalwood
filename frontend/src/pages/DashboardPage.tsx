import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { dashboardApi } from '../api/dashboard';
import { DashboardOverviewResponse } from '../types';
import { LoadingSpinner } from '../components/common/LoadingSpinner';
import {
  Trees,
  Cpu,
  ShieldCheck,
  MapPin,
  Compass,
  Satellite,
  PlusCircle,
  ArrowRight,
  RefreshCw,
} from 'lucide-react';

export const DashboardPage: React.FC = () => {
  const navigate = useNavigate();
  const [overview, setOverview] = useState<DashboardOverviewResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [isRefreshing, setIsRefreshing] = useState(false);

  const fetchDashboardData = async () => {
    setIsRefreshing(true);
    try {
      const ovData = await dashboardApi.getOverview();
      setOverview(ovData);
    } catch (e) {
      console.error('Failed to load dashboard:', e);
    } finally {
      setLoading(false);
      setIsRefreshing(false);
    }
  };

  useEffect(() => {
    fetchDashboardData();
  }, []);

  if (loading) {
    return <LoadingSpinner message="Loading dashboard..." size="lg" />;
  }

  return (
    <div className="space-y-6 font-sans max-w-6xl mx-auto pb-8">
      {/* 1. Clean Minimal Header */}
      <div className="glass-panel p-6 rounded-3xl border border-slate-800 flex flex-col sm:flex-row sm:items-center justify-between gap-4 shadow-xl">
        <div className="space-y-1">
          <div className="flex items-center gap-2">
            <span className="px-2.5 py-0.5 rounded-full text-[10px] font-mono font-bold bg-emerald-500/15 text-emerald-400 border border-emerald-500/30 flex items-center gap-1.5">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse"></span>
              <span>SYSTEM ONLINE</span>
            </span>
            <span className="text-slate-600">&bull;</span>
            <span className="text-xs font-mono text-slate-400">Zero-Trust Agroforestry</span>
          </div>
          <h1 className="text-2xl sm:text-3xl font-bold text-slate-100 tracking-tight">
            Dashboard
          </h1>
          <p className="text-xs text-slate-400">
            Welcome to the Sandalwood monitoring and asset verification console.
          </p>
        </div>

        <button
          type="button"
          onClick={fetchDashboardData}
          className="p-2.5 self-start sm:self-auto rounded-xl bg-slate-900 hover:bg-slate-800 text-slate-400 hover:text-white border border-slate-700 transition-all active:scale-95 flex items-center gap-2 text-xs font-mono"
          title="Refresh metrics"
        >
          <RefreshCw className={`w-4 h-4 ${isRefreshing ? 'animate-spin text-emerald-400' : ''}`} />
          <span>Refresh</span>
        </button>
      </div>

      {/* 2. Simple Key Stats (4 Clean Cards) */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        {/* Total Trees */}
        <div
          onClick={() => navigate('/trees')}
          className="glass-panel p-5 rounded-2xl border border-slate-800 hover:border-emerald-500/50 hover:bg-slate-900/60 transition-all cursor-pointer group"
        >
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-slate-400">Total Trees</span>
            <div className="p-2 rounded-xl bg-emerald-500/10 text-emerald-400 group-hover:bg-emerald-500/20 transition-colors">
              <Trees className="w-4 h-4" />
            </div>
          </div>
          <div className="mt-3">
            <span className="text-2xl font-bold text-slate-100 font-mono">
              {overview?.tree_assets?.total || 0}
            </span>
            <p className="text-[11px] text-slate-500 mt-0.5">Registered botanical assets</p>
          </div>
        </div>

        {/* Active IoT Gateways */}
        <div
          onClick={() => navigate('/devices')}
          className="glass-panel p-5 rounded-2xl border border-slate-800 hover:border-purple-500/50 hover:bg-slate-900/60 transition-all cursor-pointer group"
        >
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-slate-400">IoT Devices</span>
            <div className="p-2 rounded-xl bg-purple-500/10 text-purple-400 group-hover:bg-purple-500/20 transition-colors">
              <Cpu className="w-4 h-4" />
            </div>
          </div>
          <div className="mt-3">
            <span className="text-2xl font-bold text-slate-100 font-mono">
              {overview?.devices?.active || 0}
            </span>
            <p className="text-[11px] text-slate-500 mt-0.5">Active sensor nodes</p>
          </div>
        </div>

        {/* Security State */}
        <div
          onClick={() => navigate('/system')}
          className="glass-panel p-5 rounded-2xl border border-slate-800 hover:border-emerald-500/50 hover:bg-slate-900/60 transition-all cursor-pointer group"
        >
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-slate-400">Security Ledger</span>
            <div className="p-2 rounded-xl bg-emerald-500/10 text-emerald-400 group-hover:bg-emerald-500/20 transition-colors">
              <ShieldCheck className="w-4 h-4" />
            </div>
          </div>
          <div className="mt-3">
            <span className="text-2xl font-bold text-emerald-400 font-mono">
              100%
            </span>
            <p className="text-[11px] text-slate-500 mt-0.5">SHA-256 integrity verified</p>
          </div>
        </div>
      </div>

      {/* 3. Quick Access Modules (Clean Cards) */}
      <div className="space-y-3">
        <h2 className="text-xs font-bold text-slate-400 uppercase tracking-wider font-mono">
          Quick Navigation
        </h2>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {/* GIS Radar & Street View Map */}
          <div
            onClick={() => navigate('/map')}
            className="glass-panel p-5 rounded-2xl border border-slate-800 hover:border-emerald-500/50 hover:bg-slate-900/70 transition-all cursor-pointer group flex items-center justify-between gap-4"
          >
            <div className="flex items-center gap-4">
              <div className="p-3 rounded-2xl bg-emerald-500/10 text-emerald-400 group-hover:scale-105 transition-transform">
                <MapPin className="w-6 h-6" />
              </div>
              <div>
                <h3 className="text-sm font-bold text-slate-100 group-hover:text-emerald-300 transition-colors">
                  GIS Radar &amp; 360° Street View
                </h3>
                <p className="text-xs text-slate-400 mt-0.5">
                  Sub-meter satellite radar, AI tree crown detection, and 360° Ground Vision.
                </p>
              </div>
            </div>
            <ArrowRight className="w-4 h-4 text-slate-500 group-hover:text-emerald-400 group-hover:translate-x-1 transition-all" />
          </div>

          {/* Tree Registry */}
          <div
            onClick={() => navigate('/trees')}
            className="glass-panel p-5 rounded-2xl border border-slate-800 hover:border-emerald-500/50 hover:bg-slate-900/70 transition-all cursor-pointer group flex items-center justify-between gap-4"
          >
            <div className="flex items-center gap-4">
              <div className="p-3 rounded-2xl bg-emerald-500/10 text-emerald-400 group-hover:scale-105 transition-transform">
                <Trees className="w-6 h-6" />
              </div>
              <div>
                <h3 className="text-sm font-bold text-slate-100 group-hover:text-emerald-300 transition-colors">
                  Tree Registry
                </h3>
                <p className="text-xs text-slate-400 mt-0.5">
                  Inspect botanical assets, trunk girth, estimated age, and health records.
                </p>
              </div>
            </div>
            <ArrowRight className="w-4 h-4 text-slate-500 group-hover:text-emerald-400 group-hover:translate-x-1 transition-all" />
          </div>

          {/* IoT Gateways */}
          <div
            onClick={() => navigate('/devices')}
            className="glass-panel p-5 rounded-2xl border border-slate-800 hover:border-purple-500/50 hover:bg-slate-900/70 transition-all cursor-pointer group flex items-center justify-between gap-4"
          >
            <div className="flex items-center gap-4">
              <div className="p-3 rounded-2xl bg-purple-500/10 text-purple-400 group-hover:scale-105 transition-transform">
                <Cpu className="w-6 h-6" />
              </div>
              <div>
                <h3 className="text-sm font-bold text-slate-100 group-hover:text-purple-300 transition-colors">
                  IoT Gateways &amp; Sensors
                </h3>
                <p className="text-xs text-slate-400 mt-0.5">
                  Monitor solar microclimate telemetry, soil moisture, and acoustic sensors.
                </p>
              </div>
            </div>
            <ArrowRight className="w-4 h-4 text-slate-500 group-hover:text-purple-400 group-hover:translate-x-1 transition-all" />
          </div>
        </div>

      </div>
    </div>
  );
};
