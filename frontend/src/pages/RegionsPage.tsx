import React, { useEffect, useState } from 'react';
import { regionsApi } from '../api/regions';
import { Region } from '../types';
import { LoadingSpinner } from '../components/common/LoadingSpinner';
import { MapPinned } from 'lucide-react';

export const RegionsPage: React.FC = () => {
  const [regions, setRegions] = useState<Region[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    regionsApi
      .listRegions({ limit: 200 })
      .then(setRegions)
      .catch(() => setError('Could not load forest reserves.'))
      .finally(() => setLoading(false));
  }, []);

  return (
    <div className="space-y-6 font-sans">
      <div className="glass-panel p-6 rounded-3xl">
        <div className="flex items-center gap-3.5">
          <div className="p-3 rounded-2xl bg-emerald-500/15 border border-emerald-500/30 text-emerald-400">
            <MapPinned className="w-6 h-6" />
          </div>
          <div>
            <h2 className="text-xl font-bold text-slate-100 tracking-tight">Forest reserves</h2>
            <p className="text-xs text-slate-400 mt-0.5">
              Registered zones and how many trees and devices sit inside them.
            </p>
          </div>
        </div>
      </div>

      {loading && <LoadingSpinner message="Loading reserves..." />}
      {error && <p className="text-sm text-rose-300">{error}</p>}
      {!loading && !error && regions.length === 0 && (
        <p className="text-sm text-slate-400">No reserves have been registered yet.</p>
      )}
      {!loading && regions.length > 0 && (
        <div className="overflow-x-auto rounded-2xl border border-slate-800">
          <table className="w-full text-left text-xs">
            <thead className="bg-slate-900 text-slate-400">
              <tr>
                <th className="px-4 py-3 font-semibold">Code</th>
                <th className="px-4 py-3 font-semibold">Name</th>
                <th className="px-4 py-3 font-semibold">Status</th>
                <th className="px-4 py-3 font-semibold">Trees</th>
                <th className="px-4 py-3 font-semibold">Devices</th>
              </tr>
            </thead>
            <tbody>
              {regions.map((region) => (
                <tr key={region.region_id} className="border-t border-slate-800 text-slate-200">
                  <td className="px-4 py-3 font-mono">{region.region_id}</td>
                  <td className="px-4 py-3">{region.name}</td>
                  <td className="px-4 py-3">{region.status}</td>
                  <td className="px-4 py-3">{region.tree_count ?? 0}</td>
                  <td className="px-4 py-3">{region.device_count ?? 0}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
};
