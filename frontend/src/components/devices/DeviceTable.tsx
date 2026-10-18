import React from 'react';
import { Device, DeviceStatus } from '../../types';
import { DeviceStatusBadge } from '../common/Badge';
import { Cpu, ShieldAlert, CheckCircle2, Play } from 'lucide-react';
import { useAuth } from '../../context/AuthContext';

interface DeviceTableProps {
  devices: Device[];
  onToggleStatus: (deviceId: string, currentStatus: DeviceStatus) => void;
  onSimulateTelemetry?: (device: Device) => void;
}

export const DeviceTable: React.FC<DeviceTableProps> = ({
  devices,
  onToggleStatus,
  onSimulateTelemetry,
}) => {
  const { isAdmin } = useAuth();

  return (
    <div className="glass-panel rounded-2xl overflow-hidden">
      <div className="overflow-x-auto">
        <table className="w-full text-left text-xs text-slate-300">
          <thead className="bg-slate-950/60 text-[11px] uppercase tracking-wider text-slate-400 font-mono border-b border-slate-800">
            <tr>
              <th className="py-3.5 px-4 font-semibold">Device ID</th>
              <th className="py-3.5 px-4 font-semibold">Hardware Type</th>
              <th className="py-3.5 px-4 font-semibold">Last GPS Coordinate</th>
              <th className="py-3.5 px-4 font-semibold">Last Seen</th>
              <th className="py-3.5 px-4 font-semibold">Security Status</th>
              <th className="py-3.5 px-4 font-semibold text-right">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-800/60 font-mono">
            {devices.length === 0 ? (
              <tr>
                <td colSpan={6} className="py-8 text-center text-slate-500 font-sans">
                  No IoT devices registered.
                </td>
              </tr>
            ) : (
              devices.map((device) => (
                <tr key={device.id} className="hover:bg-slate-800/40 transition-colors">
                  <td className="py-3.5 px-4 font-bold text-cyan-400 flex items-center gap-2">
                    <Cpu className="w-4 h-4 text-cyan-500/70" />
                    <div>
                      <span>{device.device_id}</span>
                      <p className="text-[10px] text-slate-400 font-normal font-sans">{device.name}</p>
                    </div>
                  </td>
                  <td className="py-3.5 px-4 text-slate-300">{device.device_type}</td>
                  <td className="py-3.5 px-4 text-slate-400">
                    {device.last_latitude && device.last_longitude
                      ? `${device.last_latitude.toFixed(4)}°N, ${device.last_longitude.toFixed(4)}°E`
                      : 'Pending Check-in'}
                  </td>
                  <td className="py-3.5 px-4 text-slate-400">
                    {device.last_seen_at
                      ? new Date(device.last_seen_at).toLocaleTimeString([], {
                          hour: '2-digit',
                          minute: '2-digit',
                          second: '2-digit',
                        })
                      : 'Never'}
                  </td>
                  <td className="py-3.5 px-4">
                    <DeviceStatusBadge status={device.status} />
                  </td>
                  <td className="py-3.5 px-4 text-right">
                    <div className="flex items-center justify-end gap-2">
                      {onSimulateTelemetry && (
                        <button
                          onClick={() => onSimulateTelemetry(device)}
                          className="px-2.5 py-1 rounded-lg bg-cyan-500/15 border border-cyan-500/30 text-cyan-300 hover:bg-cyan-500/30 text-[11px] font-sans font-semibold transition-colors flex items-center gap-1"
                          title="Simulate Ingestion Packet"
                        >
                          <Play className="w-3 h-3" />
                          <span>Simulate Ingest</span>
                        </button>
                      )}

                      {isAdmin && (
                        <button
                          onClick={() => onToggleStatus(device.device_id, device.status)}
                          className={`p-1.5 rounded-lg text-xs font-medium border transition-colors ${
                            device.status === 'ACTIVE'
                              ? 'bg-rose-500/15 border-rose-500/30 text-rose-300 hover:bg-rose-500/30'
                              : 'bg-emerald-500/15 border-emerald-500/30 text-emerald-300 hover:bg-emerald-500/30'
                          }`}
                          title={device.status === 'ACTIVE' ? 'Quarantine / Revoke Device' : 'Reactivate Device'}
                        >
                          {device.status === 'ACTIVE' ? (
                            <ShieldAlert className="w-3.5 h-3.5" />
                          ) : (
                            <CheckCircle2 className="w-3.5 h-3.5" />
                          )}
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
