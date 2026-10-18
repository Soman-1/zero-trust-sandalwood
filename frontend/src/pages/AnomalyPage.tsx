import React from 'react';
import { AnomalySimulator } from '../components/anomaly/AnomalySimulator';
import { BrainCircuit, Sparkles } from 'lucide-react';

export const AnomalyPage: React.FC = () => {
  return (
    <div className="space-y-6 font-sans">
      {/* Top Banner */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 glass-panel p-6 rounded-3xl">
        <div className="flex items-center gap-3.5">
          <div className="p-3 rounded-2xl bg-purple-500/15 border border-purple-500/30 text-purple-400">
            <BrainCircuit className="w-6 h-6" />
          </div>
          <div>
            <h2 className="text-xl font-bold text-slate-100 tracking-tight">AI Anomaly Detection</h2>
            <p className="text-xs text-slate-400 mt-0.5 max-w-2xl">
              Unsupervised Isolation Forest model detecting microclimate stress and sensor telemetry outliers.
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <span className="px-3 py-1.5 rounded-xl bg-purple-500/10 text-purple-300 border border-purple-500/30 text-xs font-semibold flex items-center gap-1.5">
            <Sparkles className="w-3.5 h-3.5" />
            <span>Isolation Forest Active</span>
          </span>
        </div>
      </div>

      {/* Main AI Simulator & Model Diagnostics */}
      <AnomalySimulator />
    </div>
  );
};
