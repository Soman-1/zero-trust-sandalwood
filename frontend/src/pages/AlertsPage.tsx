import React, { useState, useEffect } from 'react';
import { alertsApi } from '../api/alerts';
import { Alert, AlertSummaryStatsResponse } from '../types';
import { AlertTable } from '../components/alerts/AlertTable';
import { AlertActionModal } from '../components/alerts/AlertActionModal';
import { AlertCreateModal } from '../components/alerts/AlertCreateModal';
import { StatCard } from '../components/common/StatCard';
import { LoadingSpinner } from '../components/common/LoadingSpinner';
import { useToast } from '../context/ToastContext';
import { useAuth } from '../context/AuthContext';
import { AlertTriangle, ShieldAlert, CheckCircle2, Plus, RefreshCw, Bell } from 'lucide-react';

export const AlertsPage: React.FC = () => {
  const { canManage } = useAuth();
  const { success, error: toastError } = useToast();
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [summaryStats, setSummaryStats] = useState<AlertSummaryStatsResponse | null>(null);
  const [loading, setLoading] = useState(true);

  // Modals state
  const [isCreateOpen, setIsCreateOpen] = useState(false);
  const [actionAlert, setActionAlert] = useState<{ alert: Alert; mode: 'resolve' | 'dismiss' } | null>(null);

  const fetchAlertsData = async () => {
    try {
      const [alertsList, stats] = await Promise.all([
        alertsApi.listAlerts({ limit: 100 }),
        alertsApi.getSummaryStats(),
      ]);
      setAlerts(alertsList.alerts || []);
      setSummaryStats(stats);
    } catch (e) {
      console.error('Failed to load alerts:', e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchAlertsData();
  }, []);

  const handleAcknowledge = async (alert: Alert) => {
    try {
      await alertsApi.acknowledgeAlert(alert.alert_uid);
      success('Alert Acknowledged', `Incident ${alert.alert_uid} marked acknowledged.`);
      fetchAlertsData();
    } catch (err: unknown) {
      toastError('Action Failed', err instanceof Error ? err.message : 'Failed to acknowledge alert.');
    }
  };

  if (loading) {
    return <LoadingSpinner message="Loading Incidents &amp; Alerts..." size="lg" />;
  }

  return (
    <div className="space-y-6 font-sans">
      {/* Top Banner */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 glass-panel p-6 rounded-3xl">
        <div className="flex items-center gap-3.5">
          <div className="p-3 rounded-2xl bg-rose-500/15 border border-rose-500/30 text-rose-400">
            <AlertTriangle className="w-6 h-6" />
          </div>
          <div>
            <h2 className="text-xl font-bold text-slate-100 tracking-tight">Alerts &amp; Incidents</h2>
            <p className="text-xs text-slate-400 mt-0.5 max-w-2xl">
              Microclimate anomalies, soil moisture warnings, and operator resolution workflows.
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2.5">
          <button
            type="button"
            onClick={fetchAlertsData}
            className="p-2.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300 transition-colors"
            title="Refresh Alerts"
          >
            <RefreshCw className="w-4 h-4" />
          </button>

          {canManage && (
            <button
              type="button"
              onClick={() => setIsCreateOpen(true)}
              className="px-4 py-2.5 rounded-xl text-xs font-semibold bg-rose-500 hover:bg-rose-600 text-white transition-all shadow-glow-rose flex items-center gap-1.5"
            >
              <Plus className="w-4 h-4" />
              <span>Create Alert</span>
            </button>
          )}
        </div>
      </div>

      {/* KPI Stats */}
      {summaryStats && (
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          <StatCard
            title="Active Alerts"
            value={summaryStats.total_active}
            subtitle="Requires Action"
            icon={Bell}
            glowColor={summaryStats.total_active > 0 ? 'rose' : 'emerald'}
          />

          <StatCard
            title="Critical"
            value={summaryStats.critical}
            subtitle="Immediate Attention"
            icon={ShieldAlert}
            glowColor={summaryStats.critical > 0 ? 'rose' : 'emerald'}
          />

          <StatCard
            title="Acknowledged"
            value={summaryStats.acknowledged}
            subtitle="Under Review"
            icon={AlertTriangle}
            glowColor="amber"
          />

          <StatCard
            title="Resolved Today"
            value={summaryStats.resolved_today}
            subtitle="Closed Issues"
            icon={CheckCircle2}
            glowColor="emerald"
          />
        </div>
      )}

      {/* Incident List Table */}
      <AlertTable
        alerts={alerts}
        onAcknowledge={handleAcknowledge}
        onResolve={(alert) => setActionAlert({ alert, mode: 'resolve' })}
        onDismiss={(alert) => setActionAlert({ alert, mode: 'dismiss' })}
      />

      {/* Action Modal (Resolve / Dismiss) */}
      <AlertActionModal
        isOpen={!!actionAlert}
        onClose={() => setActionAlert(null)}
        alert={actionAlert?.alert || null}
        mode={actionAlert?.mode || 'resolve'}
        onActionComplete={fetchAlertsData}
      />

      {/* Create Alert Modal */}
      <AlertCreateModal
        isOpen={isCreateOpen}
        onClose={() => setIsCreateOpen(false)}
        onAlertCreated={fetchAlertsData}
      />
    </div>
  );
};
