import React from 'react';
import { AuditLog } from '../../types';
import { HashDisplay } from '../common/HashDisplay';
import { Link2, ShieldCheck, UserCheck, ArrowDown, ExternalLink } from 'lucide-react';

interface HashChainViewerProps {
  logs: AuditLog[];
}

export const HashChainViewer: React.FC<HashChainViewerProps> = ({ logs }) => {
  if (logs.length === 0) {
    return (
      <div className="glass-panel p-8 rounded-2xl text-center text-slate-500 font-sans text-xs">
        No cryptographic audit records found.
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {logs.map((log, index) => (
        <div key={log.id} className="relative">
          {/* Connecting Chain Link Line */}
          {index < logs.length - 1 && (
            <div className="absolute left-6 top-16 bottom-0 w-0.5 bg-gradient-to-b from-emerald-500/50 to-slate-800 -mb-4 z-0" />
          )}

          <div className="relative z-10 glass-panel p-4 rounded-2xl hover:border-emerald-500/40 transition-all font-mono text-xs space-y-3">
            {/* Top row: Event Type & Timestamp */}
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-slate-800 pb-2.5 font-sans">
              <div className="flex items-center gap-2">
                <div className="p-1.5 rounded-lg bg-emerald-500/15 border border-emerald-500/30 text-emerald-400">
                  <ShieldCheck className="w-4 h-4" />
                </div>
                <div>
                  <span className="font-bold text-slate-100 font-mono text-xs">{log.event_type}</span>
                  <span className="text-[10px] text-slate-500 block font-mono">
                    UID: {log.audit_uid || log.log_uid}
                  </span>
                </div>
              </div>

              <div className="flex items-center gap-2 text-xs font-mono text-slate-400">
                <span>
                  {new Date(log.recorded_at || log.created_at || Date.now()).toLocaleDateString([], {
                    month: 'short',
                    day: 'numeric',
                    hour: '2-digit',
                    minute: '2-digit',
                    second: '2-digit',
                  })}
                </span>
                {(log.blockchain_tx || log.blockchain_tx_hash) && (
                  <span className="px-2 py-0.5 rounded text-[10px] bg-cyan-500/20 text-cyan-300 border border-cyan-500/40 font-mono flex items-center gap-1">
                    <span>ETH ANCHORED</span>
                  </span>
                )}
              </div>
            </div>

            {/* Event Description & Actor */}
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 font-sans text-xs">
              <div className="sm:col-span-2">
                <span className="text-[10px] text-slate-500 uppercase tracking-wider block">Action Payload</span>
                <p className="text-slate-200 mt-0.5">{log.description || log.action_detail || log.action}</p>
              </div>

              <div>
                <span className="text-[10px] text-slate-500 uppercase tracking-wider block">Actor Identity</span>
                <p className="text-slate-300 font-mono text-xs mt-0.5">
                  {log.actor_type}: {log.actor_id || 'SYSTEM'}
                </p>
              </div>
            </div>

            {/* Cryptographic SHA-256 Hashes & Blockchain Tx */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-2 pt-2 border-t border-slate-800/80">
              <div className="space-y-1">
                <span className="text-[10px] text-slate-500 uppercase tracking-wider block">Previous Block Hash</span>
                <HashDisplay hash={log.previous_hash} length={10} />
              </div>

              <div className="space-y-1">
                <span className="text-[10px] text-emerald-400 uppercase tracking-wider block font-semibold">
                  Record SHA-256 Hash Seal
                </span>
                <HashDisplay hash={log.event_hash || log.record_hash || ''} length={10} />
              </div>

              {(log.blockchain_tx || log.blockchain_tx_hash) && (
                <div className="md:col-span-2 space-y-1 pt-1 border-t border-slate-800/50">
                  <span className="text-[10px] text-cyan-400 uppercase tracking-wider block font-semibold">
                    Ethereum On-Chain Tx Hash
                  </span>
                  <HashDisplay hash={log.blockchain_tx || log.blockchain_tx_hash || ''} length={16} />
                </div>
              )}
            </div>
          </div>
        </div>
      ))}
    </div>
  );
};
