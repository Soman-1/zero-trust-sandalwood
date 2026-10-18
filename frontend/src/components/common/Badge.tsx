import React from 'react';
import { TreeStatus, DeviceStatus, AlertSeverity, AlertStatus } from '../../types';

interface BadgeProps {
  children?: React.ReactNode;
  variant?: 'healthy' | 'at_risk' | 'diseased' | 'harvested' | 'compromised' | 'active' | 'revoked' | 'critical' | 'high' | 'medium' | 'low' | 'neutral' | 'admin' | 'operator';
  className?: string;
  size?: 'sm' | 'md' | 'lg';
}

export const Badge: React.FC<BadgeProps> = ({ children, variant = 'neutral', className = '', size = 'md' }) => {
  const sizeClasses = {
    sm: 'text-[10px] px-2 py-0.5',
    md: 'text-xs px-2.5 py-0.5',
    lg: 'text-xs px-3 py-1',
  }[size];

  const dotClasses = {
    healthy: 'bg-emerald-400',
    at_risk: 'bg-amber-400',
    diseased: 'bg-rose-400',
    harvested: 'bg-slate-400',
    compromised: 'bg-rose-400',
    active: 'bg-emerald-400',
    revoked: 'bg-rose-400',
    critical: 'bg-rose-400',
    high: 'bg-amber-400',
    medium: 'bg-cyan-400',
    low: 'bg-slate-400',
    neutral: 'bg-slate-400',
    admin: 'bg-emerald-400',
    operator: 'bg-slate-300',
  }[variant];

  return (
    <span className={`inline-flex items-center gap-1.5 font-medium rounded-full bg-slate-900 border border-slate-800 text-slate-200 ${sizeClasses} ${className}`}>
      <span className={`w-1.5 h-1.5 rounded-full ${dotClasses}`}></span>
      {children}
    </span>
  );
};

export const TreeStatusBadge: React.FC<{ status: TreeStatus }> = ({ status }) => {
  const map: Record<TreeStatus, { label: string; variant: any }> = {
    HEALTHY: { label: 'Healthy', variant: 'healthy' },
    AT_RISK: { label: 'At Risk', variant: 'at_risk' },
    DISEASED: { label: 'Diseased', variant: 'diseased' },
    HARVESTED: { label: 'Harvested', variant: 'harvested' },
    REMOVED: { label: 'Removed', variant: 'harvested' },
    COMPROMISED: { label: 'Compromised', variant: 'compromised' },
  };
  const config = map[status] || { label: status, variant: 'neutral' };
  return <Badge variant={config.variant}>{config.label}</Badge>;
};

export const DeviceStatusBadge: React.FC<{ status: DeviceStatus }> = ({ status }) => {
  const map: Record<DeviceStatus, { label: string; variant: any }> = {
    ACTIVE: { label: 'Online', variant: 'active' },
    INACTIVE: { label: 'Inactive', variant: 'neutral' },
    SUSPENDED: { label: 'Suspended', variant: 'at_risk' },
    REVOKED: { label: 'Revoked', variant: 'revoked' },
    COMPROMISED: { label: 'Compromised', variant: 'compromised' },
  };
  const config = map[status] || { label: status, variant: 'neutral' };
  return <Badge variant={config.variant}>{config.label}</Badge>;
};

export const AlertSeverityBadge: React.FC<{ severity: AlertSeverity }> = ({ severity }) => {
  const map: Record<AlertSeverity, { label: string; variant: any }> = {
    CRITICAL: { label: 'Critical', variant: 'critical' },
    HIGH: { label: 'High', variant: 'high' },
    MEDIUM: { label: 'Medium', variant: 'medium' },
    LOW: { label: 'Low', variant: 'low' },
  };
  const config = map[severity] || { label: severity, variant: 'neutral' };
  return <Badge variant={config.variant} size="sm">{config.label}</Badge>;
};

export const AlertStatusBadge: React.FC<{ status: AlertStatus }> = ({ status }) => {
  const map: Record<AlertStatus, { label: string; variant: any }> = {
    ACTIVE: { label: 'Active', variant: 'critical' },
    ACKNOWLEDGED: { label: 'Acknowledged', variant: 'at_risk' },
    RESOLVED: { label: 'Resolved', variant: 'healthy' },
    DISMISSED: { label: 'Dismissed', variant: 'harvested' },
  };
  const config = map[status] || { label: status, variant: 'neutral' };
  return <Badge variant={config.variant}>{config.label}</Badge>;
};
