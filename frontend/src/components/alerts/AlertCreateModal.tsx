import React, { useState } from 'react';
import { Modal } from '../common/Modal';
import { AlertSeverity } from '../../types';
import { alertsApi } from '../../api/alerts';
import { useToast } from '../../context/ToastContext';
import { AlertTriangle, Plus } from 'lucide-react';

interface AlertCreateModalProps {
  isOpen: boolean;
  onClose: () => void;
  onAlertCreated: () => void;
}

export const AlertCreateModal: React.FC<AlertCreateModalProps> = ({
  isOpen,
  onClose,
  onAlertCreated,
}) => {
  const { success, error: toastError } = useToast();
  const [loading, setLoading] = useState(false);

  const [formData, setFormData] = useState({
    severity: 'HIGH' as AlertSeverity,
    title: '',
    description: '',
  });

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);

    try {
      await alertsApi.createAlert({
        severity: formData.severity,
        title: formData.title,
        description: formData.description,
      });

      success('Incident Created', 'New alert registered in operational ledger.');
      onAlertCreated();
      onClose();
    } catch (err: any) {
      toastError('Creation Failed', err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title="Dispatch Manual Environmental / Security Alert"
      subtitle="Broadcast urgent notification to forest department field operators"
      maxWidth="md"
    >
      <form onSubmit={handleSubmit} className="space-y-4">
        <div>
          <div>
            <label className="block text-xs font-semibold text-slate-300 mb-1">Severity Level *</label>
            <select
              value={formData.severity}
              onChange={(e) => setFormData({ ...formData, severity: e.target.value as AlertSeverity })}
              className="w-full px-3 py-2 bg-slate-950/80 border border-slate-700 rounded-xl text-xs text-slate-200 focus:border-emerald-500"
            >
              <option value="CRITICAL">Critical (Immediate Hazard)</option>
              <option value="HIGH">High (Pathogen / Drought)</option>
              <option value="MEDIUM">Medium (Anomalous Microclimate)</option>
              <option value="LOW">Low (Informational)</option>
            </select>
          </div>
        </div>

        <div>
          <label className="block text-xs font-semibold text-slate-300 mb-1">Incident Headline *</label>
          <input
            type="text"
            placeholder="e.g. Unauthorized boundary activity detected near Tree SW-KA-00007"
            value={formData.title}
            onChange={(e) => setFormData({ ...formData, title: e.target.value })}
            className="w-full px-3 py-2 bg-slate-950/80 border border-slate-700 rounded-xl text-xs text-slate-200 focus:border-emerald-500"
            required
          />
        </div>

        <div>
          <label className="block text-xs font-semibold text-slate-300 mb-1">Incident Details *</label>
          <textarea
            rows={3}
            placeholder="Provide context on physical symptoms, GPS coordinates, or patrol report..."
            value={formData.description}
            onChange={(e) => setFormData({ ...formData, description: e.target.value })}
            className="w-full px-3 py-2 bg-slate-950/80 border border-slate-700 rounded-xl text-xs text-slate-200 focus:border-emerald-500"
            required
          />
        </div>

        <div className="flex items-center justify-end gap-3 pt-3 border-t border-slate-800">
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
            className="px-5 py-2 rounded-xl text-xs font-bold bg-rose-500 hover:bg-rose-600 text-white transition-colors shadow-glow-rose flex items-center gap-1.5"
          >
            <Plus className="w-4 h-4" />
            <span>{loading ? 'Dispatching...' : 'Dispatch Alert'}</span>
          </button>
        </div>
      </form>
    </Modal>
  );
};
