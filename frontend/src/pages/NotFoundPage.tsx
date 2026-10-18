import React from 'react';
import { useNavigate } from 'react-router-dom';
import { TreePine, Home } from 'lucide-react';

export const NotFoundPage: React.FC = () => {
  const navigate = useNavigate();

  return (
    <div className="min-h-[70vh] flex flex-col items-center justify-center text-center p-4">
      <div className="p-4 rounded-3xl bg-emerald-500/15 border border-emerald-500/30 text-emerald-400 mb-4 shadow-glow-emerald">
        <TreePine className="w-12 h-12" />
      </div>
      <h1 className="text-4xl font-bold font-mono text-slate-100">404</h1>
      <h2 className="text-lg font-bold text-slate-200 mt-2">Forest Coordinate Not Found</h2>
      <p className="text-xs text-slate-400 max-w-sm mt-1 mb-6">
        The requested spatial boundary or system view does not exist in this agroforestry ledger.
      </p>
      <button
        onClick={() => navigate('/')}
        className="px-5 py-2.5 rounded-xl bg-emerald-500 hover:bg-emerald-600 text-slate-950 text-xs font-bold transition-colors shadow-glow-emerald flex items-center gap-2"
      >
        <Home className="w-4 h-4" />
        <span>Return to Executive Dashboard</span>
      </button>
    </div>
  );
};
