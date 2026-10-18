import React, { useState } from 'react';
import { Modal } from '../common/Modal';
import { Alert } from '../../types';
import { alertsApi } from '../../api/alerts';
import { useToast } from '../../context/ToastContext';
import { CheckCircle2, MessageSquare, ShieldCheck } from 'lucide-react';

interface AlertActionModalProps {
  isOpen: boolean;
  onClose: () => void;
  alert: Alert | null;
  mode: 'resolve' | 'dismiss';
  onActionComplete: () => void;
}

export const AlertActionModal: React.FC<AlertActionModalProps> = ({
  isOpen,
  onClose,
  alert,
  mode,
  onActionComplete,
}) => {
  const { success, error: toastError } = useToast();
  const [loading, setLoading] = useState(false);
  const [notes, setNotes] = useState('');

  if (!alert) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);

    try {
      if (mode === 'resolve') {
        await alertsApi.resolveAlert(alert.alert_uid, notes);
        success('Incident Resolved', `Alert ${alert.alert_uid} marked as resolved.`);
      } else {
        await alertsApi.dismissAlert(alert.alert_uid, notes);
        success('Incident Dismissed', `Alert ${alert.alert_uid} dismissed.`);
      }
      onActionComplete();
      onClose();
    } catch (err: any) {
      toastError('Action Failed', err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title={mode === 'resolve' ? 'Resolve Environmental Incident' : 'Dismiss Alert'}
      subtitle={`Incident UID: ${alert.alert_uid}`}
      maxWidth="md"
    >
      <form onSubmit={handleSubmit} className="space-y-4">
        <div className="p-3 rounded-xl bg-slate-950/60 border border-slate-800">
          <p className="text-xs font-bold text-slate-200">{alert.title}</p>
          <p className="text-[11px] text-slate-400 mt-0.5">{alert.description}</p>
        </div>

        <div>
          <label className="block text-xs font-semibold text-slate-300 mb-1 flex items-center gap-1">
            <MessageSquare className="w-3.5 h-3.5 text-emerald-400" />
            <span>Operator Resolution Notes *</span>
          </label>
          <textarea
            rows={3}
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
            placeholder={
              mode === 'resolve'
                ? 'e.g. Field inspection conducted. Drip irrigation valve restored in Sector A.'
                : 'e.g. Transient sensor calibration artifact confirmed.'
            }
            className="w-full px-3 py-2 bg-slate-950/80 border border-slate-700 rounded-xl text-xs text-slate-200 focus:outline-none focus:border-emerald-500"
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
            className={`px-5 py-2 rounded-xl text-xs font-bold text-slate-950 transition-colors flex items-center gap-1.5 ${
              mode === 'resolve'
                ? 'bg-emerald-500 hover:bg-emerald-600 shadow-glow-emerald'
                : 'bg-slate-300 hover:bg-slate-100'
            }`}
          >
            <CheckCircle2 className="w-4 h-4" />
            <span>{loading ? 'Submitting Action...' : mode === 'resolve' ? 'Sign & Resolve' : 'Dismiss Alert'}</span>
          </button>
        </div>
      </form>
    </Modal>
  );
};
