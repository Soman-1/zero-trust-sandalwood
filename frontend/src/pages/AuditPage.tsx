import React, { useState, useEffect } from 'react';
import { auditApi } from '../api/audit';
import { AuditLog, AuditChainVerifyResponse } from '../types';
import { HashChainViewer } from '../components/audit/HashChainViewer';
import { BlockchainAnchorModal } from '../components/audit/BlockchainAnchorModal';
import { HashDisplay } from '../components/common/HashDisplay';
import { LoadingSpinner } from '../components/common/LoadingSpinner';
import { useToast } from '../context/ToastContext';
import { useAuth } from '../context/AuthContext';
import {
  Link2,
  CheckCircle2,
  AlertTriangle,
  RefreshCw,
  Blocks,
  FileCheck,
} from 'lucide-react';

export const AuditPage: React.FC = () => {
  const { isAdmin } = useAuth();
  const { success, error: toastError } = useToast();
  const [logs, setLogs] = useState<AuditLog[]>([]);
  const [loading, setLoading] = useState(true);
  const [verifyingChain, setVerifyingChain] = useState(false);
  const [chainStatus, setChainStatus] = useState<AuditChainVerifyResponse | null>(null);
  const [isAnchorModalOpen, setIsAnchorModalOpen] = useState(false);

  const fetchAuditData = async () => {
    try {
      const [logsData, chainVerify] = await Promise.all([
        auditApi.listLogs({ limit: 50 }),
        auditApi.verifyChain(),
      ]);
      setLogs(logsData.logs || []);
      setChainStatus(chainVerify);
    } catch (e) {
      console.error('Failed to load audit logs:', e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchAuditData();
  }, []);

  const handleVerifyChain = async () => {
    setVerifyingChain(true);
    try {
      const res = await auditApi.verifyChain();
      setChainStatus(res);
      if (res.is_chain_valid) {
        const count = res.total_verified ?? res.total_records_checked ?? 0;
        success('Audit Chain Verified', `All ${count} SHA-256 blocks verified to genesis.`);
      } else {
        toastError('Integrity Issue', `Discrepancy at block #${res.broken_link_index}`);
      }
    } catch (err: unknown) {
      toastError('Verification Failed', err instanceof Error ? err.message : 'Hash chain verification failed.');
    } finally {
      setVerifyingChain(false);
    }
  };

  if (loading) {
    return <LoadingSpinner message="Validating Hash Chain..." size="lg" />;
  }

  return (
    <div className="space-y-6 font-sans">
      {/* Top Banner */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 glass-panel p-6 rounded-3xl">
        <div className="flex items-center gap-3.5">
          <div className="p-3 rounded-2xl bg-emerald-500/15 border border-emerald-500/30 text-emerald-400">
            <Link2 className="w-6 h-6" />
          </div>
          <div>
            <h2 className="text-xl font-bold text-slate-100 tracking-tight">Audit Ledger &amp; Blockchain</h2>
            <p className="text-xs text-slate-400 mt-0.5 max-w-2xl">
              Cryptographic hash-chaining and Merkle root anchoring to immutable smart contracts.
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2.5 flex-wrap">
          <button
            type="button"
            onClick={fetchAuditData}
            className="p-2.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300 transition-colors"
            title="Refresh Ledger"
          >
            <RefreshCw className="w-4 h-4" />
          </button>

          <button
            type="button"
            onClick={handleVerifyChain}
            disabled={verifyingChain}
            className="px-4 py-2.5 rounded-xl text-xs font-semibold bg-emerald-500 hover:bg-emerald-600 text-slate-950 transition-all shadow-glow-emerald flex items-center gap-1.5"
          >
            <FileCheck className="w-4 h-4" />
            <span>{verifyingChain ? 'Verifying...' : 'Verify Hash Chain'}</span>
          </button>

          {isAdmin && (
            <button
              type="button"
              onClick={() => setIsAnchorModalOpen(true)}
              className="px-4 py-2.5 rounded-xl text-xs font-semibold bg-purple-600 hover:bg-purple-700 text-white transition-colors flex items-center gap-1.5"
            >
              <Blocks className="w-4 h-4" />
              <span>Anchor Merkle Root</span>
            </button>
          )}
        </div>
      </div>

      {/* Chain Status Feedback Banner */}
      {chainStatus && (
        <div
          className={`p-4 rounded-2xl border flex flex-col md:flex-row md:items-center justify-between gap-4 text-xs ${
            chainStatus.is_chain_valid
              ? 'bg-emerald-950/40 border-emerald-500/50 text-emerald-300'
              : 'bg-rose-950/40 border-rose-500/50 text-rose-300'
          }`}
        >
          <div className="flex items-center gap-3">
            {chainStatus.is_chain_valid ? (
              <CheckCircle2 className="w-6 h-6 text-emerald-400 flex-shrink-0" />
            ) : (
              <AlertTriangle className="w-6 h-6 text-rose-400 flex-shrink-0" />
            )}
            <div>
              <h4 className="font-bold text-sm">
                {chainStatus.is_chain_valid ? 'Audit Hash Chain Verified Intact' : 'Integrity Issue Detected'}
              </h4>
              <p className="text-[11px] opacity-90 mt-0.5">
                {chainStatus.message} &bull; Validated {chainStatus.total_verified ?? chainStatus.total_records_checked ?? 0} sequential hash blocks.
              </p>
            </div>
          </div>

          <div className="flex flex-col sm:flex-row gap-4 pt-2 md:pt-0 border-t md:border-t-0 border-slate-800 text-[11px] font-mono">
            <div>
              <span className="text-slate-400 block font-sans">Genesis Hash:</span>
              <HashDisplay hash={chainStatus.genesis_hash || '0'.repeat(64)} length={8} />
            </div>
            <div>
              <span className="text-slate-400 block font-sans">Latest Block:</span>
              <HashDisplay hash={chainStatus.latest_hash || '0'.repeat(64)} length={8} />
            </div>
          </div>
        </div>
      )}

      {/* Hash Chain Timeline */}
      <HashChainViewer logs={logs} />

      {/* Merkle Root Smart Contract Modal */}
      <BlockchainAnchorModal
        isOpen={isAnchorModalOpen}
        onClose={() => setIsAnchorModalOpen(false)}
        onAnchorSuccess={fetchAuditData}
      />
    </div>
  );
};
