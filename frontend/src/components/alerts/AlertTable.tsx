import React, { useState } from 'react';
import { Alert, AlertSeverity, AlertStatus } from '../../types';
import { AlertSeverityBadge, AlertStatusBadge } from '../common/Badge';
import { AlertTriangle, CheckCircle2, ShieldAlert, Eye, MessageSquare } from 'lucide-react';
import { useAuth } from '../../context/AuthContext';

interface AlertTableProps {
  alerts: Alert[];
  onAcknowledge: (alert: Alert) => void;
  onResolve: (alert: Alert) => void;
  onDismiss: (alert: Alert) => void;
}

export const AlertTable: React.FC<AlertTableProps> = ({
  alerts,
  onAcknowledge,
  onResolve,
  onDismiss,
}) => {
  const { canManage } = useAuth();
  const [statusTab, setStatusTab] = useState<string>('ALL');
  const [severityFilter, setSeverityFilter] = useState<string>('ALL');

  const filteredAlerts = alerts.filter((a) => {
    const matchesStatus = statusTab === 'ALL' || a.status === statusTab;
    const matchesSeverity = severityFilter === 'ALL' || a.severity === severityFilter;
    return matchesStatus && matchesSeverity;
  });

  return (
    <div className="glass-panel rounded-2xl overflow-hidden space-y-3">
      {/* Tab bar */}
      <div className="p-4 border-b border-slate-800 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3">
        {/* Status Tabs */}
        <div className="flex items-center gap-1.5 overflow-x-auto w-full sm:w-auto pb-1 sm:pb-0">
          {(['ALL', 'ACTIVE', 'ACKNOWLEDGED', 'RESOLVED', 'DISMISSED'] as const).map((tab) => (
            <button
              key={tab}
              onClick={() => setStatusTab(tab)}
              className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-colors whitespace-nowrap ${
                statusTab === tab
                  ? 'bg-rose-500 text-white shadow-glow-rose'
                  : 'bg-slate-900 text-slate-400 hover:text-slate-200 border border-slate-800'
              }`}
            >
              {tab === 'ALL' ? 'All Incidents' : tab}
            </button>
          ))}
        </div>

        {/* Severity Filter */}
        <div className="flex items-center gap-2">
          <span className="text-xs text-slate-400">Severity:</span>
          <select
            value={severityFilter}
            onChange={(e) => setSeverityFilter(e.target.value)}
            className="px-2.5 py-1 bg-slate-950/80 border border-slate-700 rounded-lg text-xs text-slate-200"
          >
            <option value="ALL">All Severities</option>
            <option value="CRITICAL">Critical</option>
            <option value="HIGH">High</option>
            <option value="MEDIUM">Medium</option>
            <option value="LOW">Low</option>
          </select>
        </div>
      </div>

      {/* Table */}
      <div className="overflow-x-auto">
        <table className="w-full text-left text-xs text-slate-300">
          <thead className="bg-slate-950/60 text-[11px] uppercase tracking-wider text-slate-400 font-mono border-b border-slate-800">
            <tr>
              <th className="py-3 px-4 font-semibold">Severity</th>
              <th className="py-3 px-4 font-semibold">Incident Details</th>
              <th className="py-3 px-4 font-semibold">Tree</th>
              <th className="py-3 px-4 font-semibold">Timestamp</th>
              <th className="py-3 px-4 font-semibold">Status</th>
              <th className="py-3 px-4 font-semibold text-right">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-800/60 font-mono">
            {filteredAlerts.length === 0 ? (
              <tr>
                <td colSpan={6} className="py-8 text-center text-slate-500 font-sans">
                  No active incidents matching selected criteria.
                </td>
              </tr>
            ) : (
              filteredAlerts.map((alert) => (
                <tr key={alert.id} className="hover:bg-slate-800/40 transition-colors font-sans">
                  <td className="py-3.5 px-4 font-mono">
                    <AlertSeverityBadge severity={alert.severity} />
                  </td>
                  <td className="py-3.5 px-4 max-w-sm">
                    <p className="font-bold text-slate-100 text-xs">{alert.title}</p>
                    <p className="text-[11px] text-slate-400 truncate mt-0.5">{alert.description}</p>
                    {alert.resolution_notes && (
                      <p className="text-[10px] text-emerald-400/90 italic mt-1 flex items-center gap-1 font-mono">
                        <MessageSquare className="w-3 h-3" />
                        <span>Resolution: {alert.resolution_notes}</span>
                      </p>
                    )}
                  </td>
                  <td className="py-3.5 px-4 font-mono text-slate-300 text-xs">
                    {alert.tree_id ? (
                      <div className="text-emerald-400 font-semibold">Tree #{alert.tree_id}</div>
                    ) : (
                      <div className="text-slate-500">—</div>
                    )}
                  </td>
                  <td className="py-3.5 px-4 font-mono text-slate-400 text-xs">
                    {new Date(alert.created_at).toLocaleDateString([], {
                      month: 'short',
                      day: 'numeric',
                      hour: '2-digit',
                      minute: '2-digit',
                    })}
                  </td>
                  <td className="py-3.5 px-4 font-mono">
                    <AlertStatusBadge status={alert.status} />
                  </td>
                  <td className="py-3.5 px-4 text-right">
                    <div className="flex items-center justify-end gap-1.5">
                      {canManage && alert.status === 'ACTIVE' && (
                        <button
                          onClick={() => onAcknowledge(alert)}
                          className="px-2.5 py-1 rounded-lg bg-amber-500/20 text-amber-300 border border-amber-500/30 hover:bg-amber-500/30 text-xs font-semibold transition-colors"
                        >
                          Acknowledge
                        </button>
                      )}

                      {canManage && (alert.status === 'ACTIVE' || alert.status === 'ACKNOWLEDGED') && (
                        <button
                          onClick={() => onResolve(alert)}
                          className="px-2.5 py-1 rounded-lg bg-emerald-500/20 text-emerald-300 border border-emerald-500/30 hover:bg-emerald-500/30 text-xs font-semibold transition-colors"
                        >
                          Resolve
                        </button>
                      )}

                      {canManage && alert.status !== 'RESOLVED' && alert.status !== 'DISMISSED' && (
                        <button
                          onClick={() => onDismiss(alert)}
                          className="px-2 py-1 rounded-lg bg-slate-800 text-slate-400 hover:text-slate-200 text-xs transition-colors"
                        >
                          Dismiss
                        </button>
                      )}
                    </div>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
};
