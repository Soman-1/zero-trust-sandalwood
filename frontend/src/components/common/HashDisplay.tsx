import React, { useState } from 'react';
import { Copy, Check, ShieldCheck } from 'lucide-react';
import { useToast } from '../../context/ToastContext';

interface HashDisplayProps {
  hash: string;
  truncate?: boolean;
  length?: number;
  label?: string;
}

export const HashDisplay: React.FC<HashDisplayProps> = ({
  hash,
  truncate = true,
  length = 10,
  label,
}) => {
  const [copied, setCopied] = useState(false);
  const { success } = useToast();

  if (!hash) {
    return <span className="text-slate-500 text-xs italic">No hash</span>;
  }

  const displayHash =
    truncate && hash.length > length * 2
      ? `${hash.substring(0, length)}...${hash.substring(hash.length - length)}`
      : hash;

  const handleCopy = (e: React.MouseEvent) => {
    e.stopPropagation();
    navigator.clipboard.writeText(hash);
    setCopied(true);
    success('Copied Hash', 'SHA-256 cryptographic seal copied to clipboard.');
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="inline-flex items-center gap-1.5 bg-slate-950/80 border border-slate-800 hover:border-emerald-500/40 px-2 py-1 rounded-lg transition-colors group">
      <ShieldCheck className="w-3.5 h-3.5 text-emerald-400/80" />
      {label && <span className="text-[10px] text-slate-500 uppercase">{label}:</span>}
      <span className="font-mono text-xs text-slate-300 select-all" title={hash}>
        {displayHash}
      </span>
      <button
        onClick={handleCopy}
        className="text-slate-500 hover:text-emerald-400 p-0.5 rounded transition-colors"
        title="Copy full cryptographic hash"
      >
        {copied ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
      </button>
    </div>
  );
};
