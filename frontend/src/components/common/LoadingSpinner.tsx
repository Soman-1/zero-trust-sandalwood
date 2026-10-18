import React from 'react';
import { Shield } from 'lucide-react';

interface LoadingSpinnerProps {
  message?: string;
  size?: 'sm' | 'md' | 'lg';
}

export const LoadingSpinner: React.FC<LoadingSpinnerProps> = ({
  message = 'Verifying Zero Trust Ledger...',
  size = 'md',
}) => {
  const sizeClasses = {
    sm: 'w-6 h-6',
    md: 'w-10 h-10',
    lg: 'w-16 h-16',
  }[size];

  return (
    <div className="flex flex-col items-center justify-center p-8 gap-4 text-center">
      <div className="relative flex items-center justify-center">
        {/* Outer glowing pulsing ring */}
        <div
          className={`${sizeClasses} rounded-full border-2 border-emerald-500/20 border-t-emerald-400 animate-spin`}
        />
        <Shield className="w-4 h-4 text-emerald-400 absolute animate-pulse" />
      </div>
      {message && <p className="text-xs font-medium text-slate-400 font-mono tracking-wide">{message}</p>}
    </div>
  );
};
