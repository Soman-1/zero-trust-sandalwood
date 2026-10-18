import React, { useState } from 'react';
import { Modal } from '../common/Modal';
import { TreeStatus } from '../../types';
import { treesApi } from '../../api/trees';
import { useToast } from '../../context/ToastContext';
import { getApiErrorMessage } from '../../utils/apiError';
import { Trees, MapPin } from 'lucide-react';

interface TreeRegisterModalProps {
  isOpen: boolean;
  onClose: () => void;
  onTreeRegistered: () => void;
}

export const TreeRegisterModal: React.FC<TreeRegisterModalProps> = ({
  isOpen,
  onClose,
  onTreeRegistered,
}) => {
  const { success, error: toastError } = useToast();
  const [loading, setLoading] = useState(false);

  const [formData, setFormData] = useState({
    tree_uid: '',
    species: 'Santalum album',
    latitude: 13.935,
    longitude: 75.565,
    estimated_age_years: 10,
    planting_year: '' as string,
    girth_cm: 35.0,
    height_m: 7.5,
    host_notes: '',
    status: 'HEALTHY' as TreeStatus,
    notes: '',
  });

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);

    try {
      const registered = await treesApi.registerTree({
        tree_uid: formData.tree_uid.trim().toUpperCase(),
        species: formData.species,
        latitude: Number(formData.latitude),
        longitude: Number(formData.longitude),
        estimated_age_years: Number(formData.estimated_age_years),
        planting_year: formData.planting_year.trim()
          ? Number(formData.planting_year)
          : undefined,
        girth_cm: Number(formData.girth_cm),
        height_m: Number(formData.height_m),
        host_notes: formData.host_notes.trim() || undefined,
        status: formData.status,
        notes: formData.notes,
      });

      success(
        'Sandalwood Tree Registered',
        `Tree ID ${registered.tree_uid} saved with live area weather`
      );
      onTreeRegistered();
      onClose();
    } catch (err: unknown) {
      toastError('Registration Failed', getApiErrorMessage(err));
    } finally {
      setLoading(false);
    }
  };

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title="Assign Tree ID & Register"
      subtitle="You choose the Tree ID. Live area weather is stored with that ID."
      maxWidth="xl"
    >
      <form onSubmit={handleSubmit} className="space-y-4">
        <div>
          <label className="block text-xs font-semibold text-slate-300 mb-1">
            Tree ID (you assign) *
          </label>
          <input
            type="text"
            value={formData.tree_uid}
            onChange={(e) => setFormData({ ...formData, tree_uid: e.target.value.toUpperCase() })}
            placeholder="e.g. KA-01"
            pattern="[A-Za-z]{2}-[0-9]{1,5}"
            title="Format: STATE-NUMBER e.g. KA-01"
            className="w-full px-3 py-2 bg-slate-950/80 border border-slate-700 rounded-xl text-sm text-emerald-300 focus:outline-none focus:border-emerald-500 font-mono tracking-wide"
            required
          />
          <p className="mt-1 text-[11px] text-slate-500">
            Format: state code + number (KA-01, KA-00002, TN-12). Not auto-generated.
          </p>
        </div>

        <div>
          <label className="block text-xs font-semibold text-slate-300 mb-1">Botanical Species *</label>
            <input
              type="text"
              value={formData.species}
              onChange={(e) => setFormData({ ...formData, species: e.target.value })}
              className="w-full px-3 py-2 bg-slate-950/80 border border-slate-700 rounded-xl text-xs text-slate-200 focus:outline-none focus:border-emerald-500 font-mono"
              required
            />
        </div>

        <div className="p-3.5 rounded-xl bg-slate-950/60 border border-slate-800 space-y-3">
          <span className="text-xs font-semibold text-slate-200 flex items-center gap-1.5">
            <MapPin className="w-3.5 h-3.5 text-emerald-400" />
            <span>GPS Coordinates</span>
          </span>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-[11px] text-slate-400 mb-1">Latitude (°N)</label>
              <input
                type="number"
                step="0.0001"
                value={formData.latitude}
                onChange={(e) => setFormData({ ...formData, latitude: parseFloat(e.target.value) })}
                className="w-full px-3 py-1.5 bg-slate-900 border border-slate-700 rounded-lg text-xs text-slate-200 font-mono focus:border-emerald-500"
                required
              />
            </div>
            <div>
              <label className="block text-[11px] text-slate-400 mb-1">Longitude (°E)</label>
              <input
                type="number"
                step="0.0001"
                value={formData.longitude}
                onChange={(e) => setFormData({ ...formData, longitude: parseFloat(e.target.value) })}
                className="w-full px-3 py-1.5 bg-slate-900 border border-slate-700 rounded-lg text-xs text-slate-200 font-mono focus:border-emerald-500"
                required
              />
            </div>
          </div>
        </div>

        {/* Physical Attributes */}
        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="block text-xs text-slate-400 mb-1">Planting year (if known)</label>
            <input
              type="number"
              value={formData.planting_year}
              onChange={(e) => setFormData({ ...formData, planting_year: e.target.value })}
              placeholder="e.g. 2008"
              className="w-full px-3 py-2 bg-slate-950/80 border border-slate-700 rounded-xl text-xs text-slate-200 font-mono"
              min="1800"
              max={new Date().getFullYear()}
            />
          </div>
          <div>
            <label className="block text-xs text-slate-400 mb-1">Est. age if year unknown</label>
            <input
              type="number"
              value={formData.estimated_age_years}
              onChange={(e) => setFormData({ ...formData, estimated_age_years: parseInt(e.target.value) })}
              className="w-full px-3 py-2 bg-slate-950/80 border border-slate-700 rounded-xl text-xs text-slate-200 font-mono"
              min="1"
            />
          </div>
        </div>
        <p className="text-[11px] text-slate-500 -mt-2">
          A planting year is treated as the record. Without it, age stays an estimate.
        </p>

        <div>
          <label className="block text-xs text-slate-400 mb-1">Host trees nearby</label>
          <input
            type="text"
            value={formData.host_notes}
            onChange={(e) => setFormData({ ...formData, host_notes: e.target.value })}
            placeholder="e.g. Neem 4 m, Pongamia 8 m — leave blank if unknown"
            className="w-full px-3 py-2 bg-slate-950/80 border border-slate-700 rounded-xl text-xs text-slate-200 focus:outline-none focus:border-emerald-500"
          />
        </div>

        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="block text-xs text-slate-400 mb-1">Girth (cm)</label>
            <input
              type="number"
              step="0.1"
              value={formData.girth_cm}
              onChange={(e) => setFormData({ ...formData, girth_cm: parseFloat(e.target.value) })}
              className="w-full px-3 py-2 bg-slate-950/80 border border-slate-700 rounded-xl text-xs text-slate-200 font-mono"
              min="1"
            />
          </div>
          <div>
            <label className="block text-xs text-slate-400 mb-1">Height (m)</label>
            <input
              type="number"
              step="0.1"
              value={formData.height_m}
              onChange={(e) => setFormData({ ...formData, height_m: parseFloat(e.target.value) })}
              className="w-full px-3 py-2 bg-slate-950/80 border border-slate-700 rounded-xl text-xs text-slate-200 font-mono"
              min="0.5"
            />
          </div>
        </div>

        {/* Status & Notes */}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div>
            <label className="block text-xs font-semibold text-slate-300 mb-1">Initial Health Status</label>
            <select
              value={formData.status}
              onChange={(e) => setFormData({ ...formData, status: e.target.value as TreeStatus })}
              className="w-full px-3 py-2 bg-slate-950/80 border border-slate-700 rounded-xl text-xs text-slate-200 focus:outline-none focus:border-emerald-500"
            >
              <option value="HEALTHY">Healthy (Optimal Foliage)</option>
              <option value="AT_RISK">At Risk (Moisture Stress)</option>
              <option value="DISEASED">Diseased (Foliar Pathogen)</option>
              <option value="HARVESTED">Harvested (Permitted)</option>
            </select>
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-300 mb-1">Surveyor Notes</label>
            <input
              type="text"
              placeholder="e.g. Sector A mother tree, prime oil specimen"
              value={formData.notes}
              onChange={(e) => setFormData({ ...formData, notes: e.target.value })}
              className="w-full px-3 py-2 bg-slate-950/80 border border-slate-700 rounded-xl text-xs text-slate-200 focus:outline-none focus:border-emerald-500"
            />
          </div>
        </div>

        {/* Submit Buttons */}
        <div className="flex items-center justify-end gap-3 pt-4 border-t border-slate-800">
          <button
            type="button"
            onClick={onClose}
            className="px-4 py-2 rounded-xl text-xs font-semibold text-slate-400 hover:text-slate-200 bg-slate-800 hover:bg-slate-700 transition-colors"
          >
            Cancel
          </button>
          <button
            type="submit"
            disabled={loading}
            className="px-5 py-2 rounded-xl text-xs font-bold bg-emerald-500 hover:bg-emerald-600 text-slate-950 transition-colors shadow-glow-emerald flex items-center gap-1.5"
          >
            <Trees className="w-4 h-4" />
            <span>{loading ? 'Issuing Tree UID...' : 'Register Tree in Ledger'}</span>
          </button>
        </div>
      </form>
    </Modal>
  );
};
