import React, { useEffect, useState } from 'react';
import { Modal } from '../common/Modal';
import { useToast } from '../../context/ToastContext';
import { getApiErrorMessage } from '../../utils/apiError';
import { globalTreesApi } from '../../api/globalTrees';
import { GlobalTreeEnvironmentSnapshot, GlobalTreeItem } from '../../types';
import { ageLabel, gpsLabel, heartwoodEstimateLabel, survivalLabel } from '../../utils/treeAssessment';

function suggestedStateCode(state: string | null | undefined): string {
  const s = (state || '').toLowerCase();
  if (s.includes('karnataka')) return 'KA';
  if (s.includes('tamil')) return 'TN';
  if (s.includes('kerala')) return 'KL';
  if (s.includes('andhra')) return 'AP';
  if (s.includes('telangana')) return 'TG';
  if (s.includes('maharashtra')) return 'MH';
  return 'IN';
}

interface RegisterInternetTreeModalProps {
  isOpen: boolean;
  onClose: () => void;
  tree: GlobalTreeItem | null;
  environment: GlobalTreeEnvironmentSnapshot | null;
  onRegistered: (treeUid: string, environment: GlobalTreeEnvironmentSnapshot | null) => void;
}

export const RegisterInternetTreeModal: React.FC<RegisterInternetTreeModalProps> = ({
  isOpen,
  onClose,
  tree,
  environment,
  onRegistered,
}) => {
  const { success, error: toastError } = useToast();
  const [treeUid, setTreeUid] = useState('');
  const [notes, setNotes] = useState('');
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (isOpen && tree) {
      setTreeUid('');
      setNotes('');
    }
  }, [isOpen, tree?.id]);

  if (!tree) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const uid = treeUid.trim().toUpperCase();
    if (!uid) {
      toastError('Tree ID required', 'Enter an ID like KA-01');
      return;
    }
    setLoading(true);
    try {
      const res = await globalTreesApi.registerSelected({
        occurrence_id: tree.id,
        tree_uid: uid,
        notes: notes.trim() || undefined,
      });
      success(
        'Tree registered',
        res.environment_stored
          ? `${res.tree_uid} saved with GPS and environmental data`
          : `${res.tree_uid} saved with GPS. Environmental capture failed — try refresh later.`
      );
      onRegistered(res.tree_uid, res.environment);
      onClose();
    } catch (err: unknown) {
      toastError('Registration failed', getApiErrorMessage(err, 'Could not register this tree'));
    } finally {
      setLoading(false);
    }
  };

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title="Register Selected Tree"
      subtitle="Stores this specimen GPS and its live environmental data under a Tree ID you assign."
      maxWidth="xl"
    >
      <form onSubmit={handleSubmit} className="space-y-4">
        <div className="grid grid-cols-2 gap-2 text-[11px] font-mono">
          <div className="p-2.5 rounded-xl bg-slate-950/70 border border-slate-800">
            <span className="text-slate-500 block text-[9px]">LATITUDE</span>
            <span className="text-slate-100 font-bold">{tree.latitude.toFixed(7)}</span>
          </div>
          <div className="p-2.5 rounded-xl bg-slate-950/70 border border-slate-800">
            <span className="text-slate-500 block text-[9px]">LONGITUDE</span>
            <span className="text-slate-100 font-bold">{tree.longitude.toFixed(7)}</span>
          </div>
          <div className="p-2.5 rounded-xl bg-slate-950/70 border border-slate-800 col-span-2">
            <span className="text-slate-500 block text-[9px]">SOURCE</span>
            <span className="text-slate-200">
              {tree.source} · {tree.locality || tree.state_province || 'India'}
            </span>
          </div>
        </div>

        {environment ? (
          <div className="space-y-2">
            <div className="grid grid-cols-2 gap-2 text-[11px]">
              <div className="p-2.5 rounded-xl bg-emerald-950/30 border border-emerald-500/30">
                <span className="text-slate-500 block text-[9px] font-mono">TEMPERATURE</span>
                <span className="text-emerald-300 font-bold font-mono">
                  {environment.temperature_celsius.toFixed(1)}°C
                </span>
              </div>
              <div className="p-2.5 rounded-xl bg-emerald-950/30 border border-emerald-500/30">
                <span className="text-slate-500 block text-[9px] font-mono">HUMIDITY</span>
                <span className="text-emerald-300 font-bold font-mono">
                  {environment.relative_humidity_percent.toFixed(1)}%
                </span>
              </div>
              <div className="p-2.5 rounded-xl bg-emerald-950/30 border border-emerald-500/30">
                <span className="text-slate-500 block text-[9px] font-mono">SOIL MOISTURE</span>
                <span className="text-emerald-300 font-bold font-mono">
                  {environment.soil_moisture_root_percent.toFixed(1)}%
                </span>
              </div>
              <div className="p-2.5 rounded-xl bg-emerald-950/30 border border-emerald-500/30">
                <span className="text-slate-500 block text-[9px] font-mono">SUITABILITY</span>
                <span className="text-emerald-300 font-bold font-mono">
                  {environment.sandalwood_suitability_score ?? '—'}%
                </span>
              </div>
            </div>
            {tree && (
              <div className="space-y-1 text-[11px] font-mono text-slate-300">
                <p>{survivalLabel(tree.event_date)}</p>
                <p>{gpsLabel(tree.gps_accuracy)} · Hosts unknown</p>
              </div>
            )}
            {environment.heartwood && (
              <div className="grid grid-cols-2 gap-2 text-[11px]">
                <div className="p-2.5 rounded-xl bg-amber-950/20 border border-amber-500/25">
                  <span className="text-slate-500 block text-[9px] font-mono">HEARTWOOD</span>
                  <span className="text-amber-300 font-bold font-mono">
                    {heartwoodEstimateLabel(environment.heartwood.estimated_heartwood_kg)}
                  </span>
                </div>
                <div className="p-2.5 rounded-xl bg-amber-950/20 border border-amber-500/25">
                  <span className="text-slate-500 block text-[9px] font-mono">AGE / GRADE</span>
                  <span className="text-amber-200/90 font-mono text-[10px]">
                    {ageLabel(null, environment.heartwood.estimated_age_years)} ·{' '}
                    {environment.heartwood.sandalwood_grade.split(' ')[0]}
                  </span>
                </div>
              </div>
            )}
          </div>
        ) : (
          <p className="text-[11px] text-amber-300">
            Live environment is still loading. Registration will fetch and store it with the Tree ID.
          </p>
        )}

        <div>
          <label className="block text-xs font-semibold text-slate-300 mb-1">Tree ID *</label>
          <input
            type="text"
            value={treeUid}
            onChange={(e) => setTreeUid(e.target.value.toUpperCase())}
            placeholder={`e.g. ${suggestedStateCode(tree.state_province)}-01`}
            pattern="[A-Za-z]{2}-[0-9]{1,5}"
            className="w-full px-3 py-2 bg-slate-950/80 border border-slate-700 rounded-xl text-sm text-emerald-300 font-mono"
            required
          />
        </div>

        <div>
          <label className="block text-xs font-semibold text-slate-300 mb-1">Notes</label>
          <textarea
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
            rows={2}
            placeholder="Optional field note"
            className="w-full px-3 py-2 bg-slate-950/80 border border-slate-700 rounded-xl text-sm text-slate-200"
          />
        </div>

        <button
          type="submit"
          disabled={loading}
          className="w-full py-2.5 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white text-sm font-semibold disabled:opacity-50"
        >
          {loading ? 'Registering…' : 'Register coordinates & environment'}
        </button>
      </form>
    </Modal>
  );
};
