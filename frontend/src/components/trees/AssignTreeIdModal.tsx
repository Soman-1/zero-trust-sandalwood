import React, { useState } from 'react';
import { Modal } from '../common/Modal';
import { detectionsApi } from '../../api/detections';
import { treesApi } from '../../api/trees';
import { useToast } from '../../context/ToastContext';
import { getApiErrorMessage } from '../../utils/apiError';

export interface AssignTarget {
  detectionUid?: string;
  latitude: number;
  longitude: number;
  species?: string;
  source?: string;
  evidenceOrigin?: string;
}

interface AssignTreeIdModalProps {
  isOpen: boolean;
  onClose: () => void;
  target: AssignTarget | null;
  regions?: unknown;
  onAssigned: () => void;
}

export const AssignTreeIdModal: React.FC<AssignTreeIdModalProps> = ({
  isOpen,
  onClose,
  target,
  onAssigned,
}) => {
  const { success, error: toastError } = useToast();
  const [treeUid, setTreeUid] = useState('');
  const [loading, setLoading] = useState(false);

  if (!target) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const uid = treeUid.trim().toUpperCase();
    if (!uid) {
      toastError('Tree ID required', 'Enter an ID like KA-01');
      return;
    }
    if ((target.evidenceOrigin || '').toUpperCase() === 'SIMULATED') {
      toastError('Simulated detection', 'This overlay is not a field survey and cannot be saved as a tree.');
      return;
    }
    setLoading(true);
    try {
      if (target.detectionUid) {
        const tree = await detectionsApi.assignTreeId(target.detectionUid, {
          tree_uid: uid,
          species: target.species || 'Santalum album',
        });
        success('Tree ID Assigned', `${tree.tree_uid} saved with live weather`);
      } else {
        const tree = await treesApi.registerTree({
          tree_uid: uid,
          latitude: target.latitude,
          longitude: target.longitude,
          species: target.species || 'Santalum album',
          notes: target.source ? `Assigned from ${target.source}` : undefined,
          evidence_origin: target.evidenceOrigin,
        });
        success('Tree Registered', `${tree.tree_uid} saved with live weather`);
      }
      setTreeUid('');
      onAssigned();
      onClose();
    } catch (err: unknown) {
      toastError('Assign Failed', getApiErrorMessage(err));
    } finally {
      setLoading(false);
    }
  };

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title="Assign Tree ID"
      subtitle="Detection has GPS only. You choose the Tree ID."
      maxWidth="md"
    >
      <form onSubmit={handleSubmit} className="space-y-4">
        <div className="p-3 rounded-xl bg-slate-950/60 border border-slate-800 text-xs text-slate-300 space-y-1 font-mono">
          <div>Lat: {target.latitude.toFixed(5)}</div>
          <div>Lon: {target.longitude.toFixed(5)}</div>
          {target.detectionUid && <div>Detection: {target.detectionUid}</div>}
          {target.source && <div>Source: {target.source}</div>}
          <div className="text-amber-300 font-sans font-semibold pt-1">No Tree ID yet</div>
        </div>

        <div>
          <label className="block text-xs font-semibold text-slate-300 mb-1">Tree ID *</label>
          <input
            type="text"
            value={treeUid}
            onChange={(e) => setTreeUid(e.target.value.toUpperCase())}
            placeholder="e.g. KA-01"
            pattern="[A-Za-z]{2}-[0-9]{1,5}"
            className="w-full px-3 py-2 bg-slate-950/80 border border-slate-700 rounded-xl text-sm text-emerald-300 font-mono"
            required
          />
        </div>

        <p className="text-[11px] text-slate-500">
          Saves this GPS and live weather (temperature, humidity, soil) with the Tree ID. No reserve or area is required.
        </p>

        <button
          type="submit"
          disabled={loading}
          className="w-full py-2.5 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white text-sm font-semibold disabled:opacity-50"
        >
          {loading ? 'Saving…' : 'Assign ID & Store Weather'}
        </button>
      </form>
    </Modal>
  );
};
