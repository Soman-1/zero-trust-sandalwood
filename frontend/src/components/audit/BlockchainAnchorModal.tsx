import React, { useState } from 'react';
import { Modal } from '../common/Modal';
import { auditApi } from '../../api/audit';
import { BlockchainAnchorResponse } from '../../types';
import { HashDisplay } from '../common/HashDisplay';
import { useToast } from '../../context/ToastContext';
import { getApiErrorMessage } from '../../utils/apiError';
import { CheckCircle2, Blocks, AlertTriangle } from 'lucide-react';

interface BlockchainAnchorModalProps {
  isOpen: boolean;
  onClose: () => void;
  onAnchorSuccess: () => void;
}

export const BlockchainAnchorModal: React.FC<BlockchainAnchorModalProps> = ({
  isOpen,
  onClose,
  onAnchorSuccess,
}) => {
  const { success, error: toastError } = useToast();
  const [loading, setLoading] = useState(false);
  const [batchSize, setBatchSize] = useState(50);
  const [anchorResult, setAnchorResult] = useState<BlockchainAnchorResponse | null>(null);

  const handleAnchor = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setAnchorResult(null);

    try {
      const res = await auditApi.anchorToBlockchain(batchSize);
      setAnchorResult(res);

      if (!res.success) {
        toastError(
          'Anchoring Not Completed',
          res.message || 'Chain unavailable or nothing to anchor.',
        );
        return;
      }

      const count = res.records_anchored ?? res.anchored_records ?? 0;
      success('Merkle Root Anchored', `Anchored ${count} records to Smart Contract.`);
      onAnchorSuccess();
    } catch (err: unknown) {
      toastError('Anchoring Error', getApiErrorMessage(err));
    } finally {
      setLoading(false);
    }
  };

  const anchoredCount =
    anchorResult?.records_anchored ?? anchorResult?.anchored_records ?? 0;
  const txHash = anchorResult?.transaction_hash || anchorResult?.tx_hash || '';
  const showSuccessPanel = Boolean(anchorResult?.success && txHash);

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title="Ethereum Blockchain Evidence Anchoring"
      subtitle="Compute cryptographic Merkle Root over pending audit logs and anchor to smart contract"
      maxWidth="lg"
    >
      <div className="space-y-4">
        <form onSubmit={handleAnchor} className="space-y-4">
          <div className="p-4 rounded-xl bg-slate-950 border border-slate-800 space-y-2">
            <div className="flex items-center justify-between text-xs">
              <span className="text-slate-400">Target Smart Contract:</span>
              <span className="font-mono text-emerald-400">
                {anchorResult?.contract_address || 'Configured via BLOCKCHAIN_CONTRACT_ADDRESS'}
              </span>
            </div>
            <div className="flex items-center justify-between text-xs">
              <span className="text-slate-400">EVM Chain ID:</span>
              <span className="font-mono text-cyan-400">
                {anchorResult?.chain_id || 31337} (Hardhat / Local)
              </span>
            </div>
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-300 mb-1">
              Audit Batch Size (Max Records to Anchor)
            </label>
            <input
              type="number"
              min="1"
              max="500"
              value={Number.isNaN(batchSize) ? '' : batchSize}
              onChange={(e) => {
                const next = parseInt(e.target.value, 10);
                setBatchSize(Number.isNaN(next) ? 1 : Math.min(500, Math.max(1, next)));
              }}
              className="w-full px-3 py-2 bg-slate-950/80 border border-slate-700 rounded-xl text-xs text-slate-200 font-mono focus:border-emerald-500"
              required
            />
          </div>

          <div className="flex items-center justify-end gap-3 pt-2">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 rounded-xl text-xs font-semibold text-slate-400 hover:text-slate-200 bg-slate-800 hover:bg-slate-700 transition-colors"
            >
              Close
            </button>
            <button
              type="submit"
              disabled={loading}
              className="px-5 py-2 rounded-xl text-xs font-bold bg-purple-600 hover:bg-purple-700 text-white transition-colors shadow-lg flex items-center gap-2"
            >
              <Blocks className="w-4 h-4" />
              <span>{loading ? 'Executing Merkle Anchor...' : 'Compute & Anchor Batch'}</span>
            </button>
          </div>
        </form>

        {anchorResult && !anchorResult.success && (
          <div className="p-4 rounded-xl bg-amber-950/40 border border-amber-500/50 space-y-2 font-mono text-xs">
            <div className="flex items-center gap-2 text-amber-300 font-bold">
              <AlertTriangle className="w-5 h-5 text-amber-400" />
              <span>Anchor Not Confirmed</span>
            </div>
            <p className="text-slate-300 font-sans text-[11px]">{anchorResult.message}</p>
          </div>
        )}

        {showSuccessPanel && (
          <div className="p-4 rounded-xl bg-emerald-950/40 border border-emerald-500/60 space-y-3 font-mono text-xs">
            <div className="flex items-center gap-2 text-emerald-300 font-bold">
              <CheckCircle2 className="w-5 h-5 text-emerald-400" />
              <span>Batch Anchored to SandalwoodAuditRegistry</span>
            </div>

            <div className="space-y-2 pt-2 border-t border-emerald-500/30 text-[11px]">
              <div>
                <span className="text-slate-400 block font-sans">Anchored Records Count:</span>
                <span className="font-bold text-slate-100">{anchoredCount}</span>
              </div>

              <div>
                <span className="text-slate-400 block font-sans">Cryptographic Merkle Root:</span>
                <HashDisplay hash={anchorResult!.merkle_root} length={16} />
              </div>

              <div>
                <span className="text-slate-400 block font-sans">Blockchain TX Hash:</span>
                <HashDisplay hash={txHash} length={16} />
              </div>
            </div>
          </div>
        )}
      </div>
    </Modal>
  );
};
