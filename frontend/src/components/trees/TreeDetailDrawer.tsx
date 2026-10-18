import React, { useState, useEffect } from 'react';
import { Tree, EnvironmentalMeasurement, IntegrityCheckResponse, TreeStatus } from '../../types';
import { measurementsApi } from '../../api/measurements';
import { treesApi } from '../../api/trees';
import { ageLabel, gpsLabel, hostsLabel } from '../../utils/treeAssessment';
import { TreeStatusBadge } from '../common/Badge';
import { HashDisplay } from '../common/HashDisplay';
import { useToast } from '../../context/ToastContext';
import { useAuth } from '../../context/AuthContext';
import {
  X,
  Trees,
  Thermometer,
  Droplets,
  ShieldCheck,
  CheckCircle2,
  AlertTriangle,
  RefreshCw,
  Gauge,
  Trash2,
} from 'lucide-react';

interface TreeDetailDrawerProps {
  tree: Tree | null;
  onClose: () => void;
  onTreeUpdated?: () => void;
  onDeleteTree?: (tree: Tree) => void;
}

export const TreeDetailDrawer: React.FC<TreeDetailDrawerProps> = ({
  tree,
  onClose,
  onTreeUpdated,
  onDeleteTree,
}) => {
  const { canManage } = useAuth();
  const { success, error: toastError } = useToast();
  const [latestMeasurement, setLatestMeasurement] = useState<EnvironmentalMeasurement | null>(null);
  const [loadingTelemetry, setLoadingTelemetry] = useState(false);
  const [verifyingHash, setVerifyingHash] = useState(false);
  const [integrityResult, setIntegrityResult] = useState<IntegrityCheckResponse | null>(null);
  const [updatingStatus, setUpdatingStatus] = useState(false);

  useEffect(() => {
    if (!tree) return;
    setIntegrityResult(null);
    const fetchLatest = async () => {
      setLoadingTelemetry(true);
      try {
        const meas = await measurementsApi.getLatestForTree(tree.tree_uid);
        setLatestMeasurement(meas);
      } catch {
        setLatestMeasurement(null);
      } finally {
        setLoadingTelemetry(false);
      }
    };
    fetchLatest();
  }, [tree]);

  if (!tree) return null;

  const handleVerifyIntegrity = async () => {
    if (!latestMeasurement) return;
    setVerifyingHash(true);
    try {
      const res = await measurementsApi.verifyMeasurementIntegrity(latestMeasurement.measurement_uid);
      setIntegrityResult(res);
      if (res.is_valid) {
        success('Zero Trust Hash Verified', 'Cryptographic SHA-256 seal matches database record.');
      } else {
        toastError('Integrity Breach Alert', 'Stored hash does NOT match calculated canonical bytes!');
      }
    } catch (err: unknown) {
      toastError('Verification Failed', err instanceof Error ? err.message : 'Verification failed.');
    } finally {
      setVerifyingHash(false);
    }
  };

  const handleStatusChange = async (newStatus: TreeStatus) => {
    setUpdatingStatus(true);
    try {
      await treesApi.updateTree(tree.tree_uid, { status: newStatus });
      success('Health Status Updated', `Tree ${tree.tree_uid} marked as ${newStatus}.`);
      if (onTreeUpdated) onTreeUpdated();
    } catch (err: unknown) {
      toastError('Update Failed', err instanceof Error ? err.message : 'Status update failed.');
    } finally {
      setUpdatingStatus(false);
    }
  };

  return (
    <div className="fixed inset-y-0 right-0 z-50 w-full max-w-md bg-slate-900 border-l border-slate-800 shadow-2xl flex flex-col animate-slide-in">
      {/* Header */}
      <div className="p-5 border-b border-slate-800 flex items-center justify-between bg-slate-950/60">
        <div className="flex items-center gap-2.5">
          <div className="p-2 rounded-xl bg-emerald-500/20 text-emerald-400 border border-emerald-500/30">
            <Trees className="w-5 h-5" />
          </div>
          <div>
            <h3 className="font-bold text-base font-mono text-slate-100">{tree.tree_uid}</h3>
            <p className="text-xs italic text-slate-400">{tree.species}</p>
          </div>
        </div>
        <div className="flex items-center gap-1">
          {onDeleteTree && (
            <button
              type="button"
              onClick={() => onDeleteTree(tree)}
              className="p-2 rounded-lg text-slate-400 hover:text-rose-300 hover:bg-rose-950/60 transition-colors"
              title="Delete Tree"
            >
              <Trash2 className="w-4 h-4" />
            </button>
          )}
          <button
            onClick={onClose}
            className="p-2 rounded-lg text-slate-400 hover:text-slate-100 hover:bg-slate-800 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>
      </div>

      {/* Drawer Content */}
      <div className="flex-1 overflow-y-auto p-5 space-y-5">
        {/* Status & Quick Change */}
        <div className="glass-panel p-4 rounded-xl space-y-3">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold uppercase text-slate-400">Current Health</span>
            <TreeStatusBadge status={tree.status} />
          </div>

          {canManage && (
            <div className="pt-2 border-t border-slate-800">
              <label className="block text-[11px] text-slate-400 mb-1.5 font-medium">
                Update Health Classification:
              </label>
              <div className="grid grid-cols-2 gap-2">
                {(['HEALTHY', 'AT_RISK', 'DISEASED', 'HARVESTED'] as TreeStatus[]).map((st) => (
                  <button
                    key={st}
                    onClick={() => handleStatusChange(st)}
                    disabled={updatingStatus || tree.status === st}
                    className={`py-1.5 px-2 rounded-lg text-[11px] font-semibold border transition-all ${
                      tree.status === st
                        ? 'bg-emerald-500/20 border-emerald-500/50 text-emerald-300'
                        : 'bg-slate-950/60 border-slate-800 text-slate-400 hover:text-slate-200 hover:border-slate-700'
                    }`}
                  >
                    {st.replace('_', ' ')}
                  </button>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Physical Bio-Attributes */}
        <div className="glass-panel p-4 rounded-xl space-y-3 font-mono text-xs">
          <h4 className="font-bold text-slate-200 font-sans text-xs uppercase tracking-wider flex items-center gap-1.5">
            <Trees className="w-3.5 h-3.5 text-emerald-400" />
            <span>Biometric Traits</span>
          </h4>

          <div className="space-y-1 text-[11px] text-slate-300">
            <p>
              {tree.age_label ||
                ageLabel(tree.planting_year, tree.estimated_age_years, tree.biometrics_source)}
            </p>
            <p>{tree.survival_label || `Confirmed ${tree.status.replace(/_/g, ' ')}`}</p>
            <p>{tree.hosts_label || hostsLabel(tree.host_notes)}</p>
            <p>{tree.heartwood_label || 'Heartwood unknown (needs measured girth and height)'}</p>
            <p>{tree.gps_label || gpsLabel(tree.gps_accuracy)}</p>
          </div>

          <div className="grid grid-cols-3 gap-2 text-center">
            <div className="bg-slate-950/60 p-2.5 rounded-lg border border-slate-800">
              <span className="text-[10px] text-slate-500 block">Age</span>
              <span className="font-bold text-slate-200 text-sm">{tree.estimated_age_years || 'N/A'}y</span>
            </div>
            <div className="bg-slate-950/60 p-2.5 rounded-lg border border-slate-800">
              <span className="text-[10px] text-slate-500 block">Girth</span>
              <span className="font-bold text-slate-200 text-sm">{tree.girth_cm || 'N/A'}cm</span>
            </div>
            <div className="bg-slate-950/60 p-2.5 rounded-lg border border-slate-800">
              <span className="text-[10px] text-slate-500 block">Height</span>
              <span className="font-bold text-slate-200 text-sm">{tree.height_m || 'N/A'}m</span>
            </div>
          </div>

          <div className="pt-2 border-t border-slate-800 text-slate-400 text-[11px] space-y-1">
            <div>
              <span className="text-slate-500">Coordinates:</span> {tree.latitude.toFixed(6)}°N,{' '}
              {tree.longitude.toFixed(6)}°E
            </div>
            {tree.notes && (
              <div>
                <span className="text-slate-500">Notes:</span> {tree.notes}
              </div>
            )}
          </div>
        </div>

        {/* Latest Microclimate Telemetry */}
        <div className="glass-panel p-4 rounded-xl space-y-3">
          <div className="flex items-center justify-between">
            <h4 className="font-bold text-slate-200 text-xs uppercase tracking-wider flex items-center gap-1.5">
              <Thermometer className="w-3.5 h-3.5 text-cyan-400" />
              <span>Latest Microclimate</span>
            </h4>
            {loadingTelemetry && <RefreshCw className="w-3.5 h-3.5 text-slate-400 animate-spin" />}
          </div>

          {latestMeasurement ? (
            <div className="space-y-3">
              <div className="grid grid-cols-3 gap-2 text-center font-mono">
                <div className="p-2 rounded-lg bg-rose-500/10 border border-rose-500/20 text-rose-300">
                  <span className="text-[10px] block opacity-80">Ambient Temp</span>
                  <span className="font-bold text-sm">{latestMeasurement.temperature}°C</span>
                </div>
                <div className="p-2 rounded-lg bg-cyan-500/10 border border-cyan-500/20 text-cyan-300">
                  <span className="text-[10px] block opacity-80">Humidity</span>
                  <span className="font-bold text-sm">{latestMeasurement.humidity}%</span>
                </div>
                <div className="p-2 rounded-lg bg-emerald-500/10 border border-emerald-500/20 text-emerald-300">
                  <span className="text-[10px] block opacity-80">Soil Moisture</span>
                  <span className="font-bold text-sm">{latestMeasurement.soil_moisture}%</span>
                </div>
              </div>

              {/* Cryptographic SHA-256 Seal */}
              <div className="p-3 rounded-lg bg-slate-950/80 border border-slate-800 space-y-2">
                <div className="flex items-center justify-between">
                  <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400">
                    SHA-256 Canonical Seal
                  </span>
                  <button
                    onClick={handleVerifyIntegrity}
                    disabled={verifyingHash}
                    className="flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-bold bg-emerald-500/20 text-emerald-300 border border-emerald-500/40 hover:bg-emerald-500/30 transition-colors"
                  >
                    <ShieldCheck className="w-3 h-3" />
                    <span>{verifyingHash ? 'Verifying...' : 'Verify Zero Trust Seal'}</span>
                  </button>
                </div>

                <HashDisplay hash={latestMeasurement.integrity_hash} length={12} />

                {integrityResult && (
                  <div
                    className={`p-2 rounded text-xs flex items-center gap-2 mt-1 ${
                      integrityResult.is_valid
                        ? 'bg-emerald-950/60 border border-emerald-500/50 text-emerald-300'
                        : 'bg-rose-950/60 border border-rose-500/50 text-rose-300'
                    }`}
                  >
                    {integrityResult.is_valid ? (
                      <CheckCircle2 className="w-4 h-4 text-emerald-400 flex-shrink-0" />
                    ) : (
                      <AlertTriangle className="w-4 h-4 text-rose-400 flex-shrink-0" />
                    )}
                    <span className="text-[11px]">{integrityResult.message}</span>
                  </div>
                )}
              </div>
            </div>
          ) : (
            <p className="text-xs text-slate-500 italic">No microclimate reading captured yet for this tree.</p>
          )}
        </div>
      </div>
    </div>
  );
};
