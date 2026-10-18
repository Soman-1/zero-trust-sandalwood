import React, { useState, useEffect } from 'react';
import { systemApi } from '../api/system';
import { authApi } from '../api/auth';
import { SystemInfoResponse, User, UserRole, UserStatus } from '../types';
import { LoadingSpinner } from '../components/common/LoadingSpinner';
import { Badge } from '../components/common/Badge';
import { useToast } from '../context/ToastContext';
import { useAuth } from '../context/AuthContext';
import {
  Settings,
  ShieldCheck,
  Database,
  Cpu,
  BrainCircuit,
  Users,
  CheckCircle2,
  AlertTriangle,
  RefreshCw,
  Lock,
} from 'lucide-react';

export const SystemPage: React.FC = () => {
  const { isAdmin, user: currentUser } = useAuth();
  const { success, error: toastError } = useToast();
  const [sysInfo, setSysInfo] = useState<SystemInfoResponse | null>(null);
  const [users, setUsers] = useState<User[]>([]);
  const [loading, setLoading] = useState(true);

  const fetchSystemData = async () => {
    try {
      const info = await systemApi.getSystemInfo();
      setSysInfo(info);

      if (isAdmin) {
        const usersResp = await authApi.listUsers();
        setUsers(usersResp.users || []);
      }
    } catch (e) {
      console.error('System info fetch error:', e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchSystemData();
  }, [isAdmin]);

  const handleToggleUserStatus = async (user: User) => {
    const nextStatus: UserStatus = user.status === 'ACTIVE' ? 'SUSPENDED' : 'ACTIVE';
    try {
      await authApi.updateUserStatus(user.id, nextStatus);
      success('User Status Updated', `User ${user.username} is now ${nextStatus}.`);
      fetchSystemData();
    } catch (err: unknown) {
      toastError('Update Failed', err instanceof Error ? err.message : 'User status update failed.');
    }
  };

  const handleChangeUserRole = async (user: User, newRole: UserRole) => {
    try {
      await authApi.updateUserRole(user.id, newRole);
      success('Role Assigned', `User ${user.username} role changed to ${newRole}.`);
      fetchSystemData();
    } catch (err: unknown) {
      toastError('Update Failed', err instanceof Error ? err.message : 'Role update failed.');
    }
  };

  if (loading) {
    return <LoadingSpinner message="Querying Zero Trust System Diagnostics..." size="lg" />;
  }

  return (
    <div className="space-y-6">
      {/* Top Banner */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 glass-panel p-6 rounded-3xl">
        <div className="flex items-center gap-3.5">
          <div className="p-3 rounded-2xl bg-cyan-500/15 border border-cyan-500/30 text-cyan-400">
            <Settings className="w-6 h-6" />
          </div>
          <div>
            <h2 className="text-xl font-bold text-slate-100">Zero Trust Framework Diagnostics</h2>
            <p className="text-xs text-slate-400 mt-0.5">
              Service telemetry, microservice health, database connectivity, and role-based user management.
            </p>
          </div>
        </div>

        <button
          onClick={fetchSystemData}
          className="p-2.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300 transition-colors self-start sm:self-auto"
          title="Refresh Diagnostics"
        >
          <RefreshCw className="w-4 h-4" />
        </button>
      </div>

      {/* Health & Architecture Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {/* Core Backend Status */}
        <div className="glass-panel p-5 rounded-2xl space-y-3 font-mono text-xs">
          <div className="flex items-center gap-2 border-b border-slate-800 pb-2.5 font-sans">
            <ShieldCheck className="w-4 h-4 text-emerald-400" />
            <h3 className="font-bold text-slate-100 text-sm">Security Gateway</h3>
          </div>

          <div className="space-y-2">
            <div className="flex justify-between">
              <span className="text-slate-400 font-sans">Framework Mode:</span>
              <span className="text-emerald-400 font-bold">ZERO TRUST ENFORCED</span>
            </div>
            <div className="flex justify-between">
              <span className="text-slate-400 font-sans">Anti-Replay Window:</span>
              <span className="text-slate-200">±900s (15 min drift window)</span>
            </div>
            <div className="flex justify-between">
              <span className="text-slate-400 font-sans">Canonical Integrity:</span>
              <span className="text-slate-200">SHA-256 Hash Chain</span>
            </div>
            <div className="flex justify-between">
              <span className="text-slate-400 font-sans">Blockchain Anchor:</span>
              <span className="text-cyan-400">Merkle Root on EVM</span>
            </div>
          </div>
        </div>

        {/* Database & Connectivity */}
        <div className="glass-panel p-5 rounded-2xl space-y-3 font-mono text-xs">
          <div className="flex items-center gap-2 border-b border-slate-800 pb-2.5 font-sans">
            <Database className="w-4 h-4 text-cyan-400" />
            <h3 className="font-bold text-slate-100 text-sm">Database &amp; Ledger</h3>
          </div>

          <div className="space-y-2">
            <div className="flex justify-between">
              <span className="text-slate-400 font-sans">DB Engine:</span>
              <span className="text-slate-200">SQLite / PostgreSQL</span>
            </div>
            <div className="flex justify-between">
              <span className="text-slate-400 font-sans">DB Status:</span>
              <span className="text-emerald-400 font-bold">{sysInfo?.database_status || 'CONNECTED'}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-slate-400 font-sans">Total Audit Logs:</span>
              <span className="text-slate-200">{sysInfo?.total_audit_logs || 0} Records</span>
            </div>
            <div className="flex justify-between">
              <span className="text-slate-400 font-sans">API Version:</span>
              <span className="text-slate-200">{sysInfo?.version || '1.0.0'} [{sysInfo?.environment}]</span>
            </div>
          </div>
        </div>

        {/* AI Engine Status */}
        <div className="glass-panel p-5 rounded-2xl space-y-3 font-mono text-xs">
          <div className="flex items-center gap-2 border-b border-slate-800 pb-2.5 font-sans">
            <BrainCircuit className="w-4 h-4 text-purple-400" />
            <h3 className="font-bold text-slate-100 text-sm">AI Anomaly Engine</h3>
          </div>

          <div className="space-y-2">
            <div className="flex justify-between">
              <span className="text-slate-400 font-sans">Architecture:</span>
              <span className="text-purple-300 font-bold">{sysInfo?.ai_model_type || 'IsolationForest'}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-slate-400 font-sans">Model Fitted:</span>
              <span className="text-emerald-400 font-bold">{sysInfo?.ai_model_fitted ? 'YES' : 'NO'}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-slate-400 font-sans">Trained Samples:</span>
              <span className="text-slate-200">{sysInfo?.ai_trained_samples || 0} Telemetry Points</span>
            </div>
            <div className="flex justify-between">
              <span className="text-slate-400 font-sans">Feature Pipelines:</span>
              <span className="text-slate-200">Temp, Hum, Soil, VPD</span>
            </div>
          </div>
        </div>
      </div>

      {/* Admin User Management Table (Admin Only) */}
      {isAdmin && (
        <div className="glass-panel rounded-2xl overflow-hidden space-y-3">
          <div className="p-4 border-b border-slate-800 flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Users className="w-4 h-4 text-purple-400" />
              <h3 className="text-sm font-bold text-slate-100">User Identity &amp; Role Administration</h3>
            </div>
            <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-purple-500/15 text-purple-300 border border-purple-500/30">
              ADMINISTRATIVE PRIVILEGES
            </span>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs text-slate-300 font-mono">
              <thead className="bg-slate-950/60 text-[11px] uppercase tracking-wider text-slate-400 border-b border-slate-800">
                <tr>
                  <th className="py-3 px-4 font-semibold">User</th>
                  <th className="py-3 px-4 font-semibold">Role</th>
                  <th className="py-3 px-4 font-semibold">Status</th>
                  <th className="py-3 px-4 font-semibold">Created At</th>
                  <th className="py-3 px-4 font-semibold text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60">
                {users.map((u) => (
                  <tr key={u.id} className="hover:bg-slate-800/40 transition-colors font-sans">
                    <td className="py-3 px-4 font-mono">
                      <span className="font-bold text-slate-100">{u.username}</span>
                      <p className="text-[11px] text-slate-400">{u.email}</p>
                    </td>
                    <td className="py-3 px-4">
                      <select
                        value={u.role}
                        onChange={(e) => handleChangeUserRole(u, e.target.value as UserRole)}
                        disabled={u.id === currentUser?.id}
                        className="px-2 py-1 bg-slate-950 border border-slate-700 rounded-lg text-xs text-slate-200 font-mono focus:border-purple-500"
                      >
                        <option value="ADMIN">ADMIN</option>
                        <option value="OPERATOR">OPERATOR</option>
                        <option value="AUDITOR">AUDITOR</option>
                        <option value="VIEWER">VIEWER</option>
                      </select>
                    </td>
                    <td className="py-3 px-4">
                      <Badge
                        variant={
                          u.status === 'ACTIVE' ? 'active' : u.status === 'SUSPENDED' ? 'revoked' : 'neutral'
                        }
                      >
                        {u.status}
                      </Badge>
                    </td>
                    <td className="py-3 px-4 text-slate-400 font-mono text-xs">
                      {new Date(u.created_at).toLocaleDateString([], {
                        year: 'numeric',
                        month: 'short',
                        day: 'numeric',
                      })}
                    </td>
                    <td className="py-3 px-4 text-right">
                      {u.id !== currentUser?.id && (
                        <button
                          onClick={() => handleToggleUserStatus(u)}
                          className={`px-2.5 py-1 rounded-lg text-xs font-semibold border transition-colors ${
                            u.status === 'ACTIVE'
                              ? 'bg-rose-500/15 border-rose-500/30 text-rose-300 hover:bg-rose-500/30'
                              : 'bg-emerald-500/15 border-emerald-500/30 text-emerald-300 hover:bg-emerald-500/30'
                          }`}
                        >
                          {u.status === 'ACTIVE' ? 'Suspend Account' : 'Reactivate'}
                        </button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
};
