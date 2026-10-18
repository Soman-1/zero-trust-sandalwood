import React, { useState, useEffect } from 'react';
import { devicesApi } from '../api/devices';
import { Device, DeviceStatus } from '../types';
import { DeviceTable } from '../components/devices/DeviceTable';
import { DeviceRegisterModal } from '../components/devices/DeviceRegisterModal';
import { DeviceSimulatorModal } from '../components/devices/DeviceSimulatorModal';
import { LoadingSpinner } from '../components/common/LoadingSpinner';
import { useToast } from '../context/ToastContext';
import { useAuth } from '../context/AuthContext';
import { Cpu, Plus, RefreshCw } from 'lucide-react';

export const DevicesPage: React.FC = () => {
  const { canManage } = useAuth();
  const { success, error: toastError } = useToast();
  const [devices, setDevices] = useState<Device[]>([]);
  const [loading, setLoading] = useState(true);
  const [isRegisterOpen, setIsRegisterOpen] = useState(false);
  const [simulatorDevice, setSimulatorDevice] = useState<Device | null>(null);

  const fetchDevices = async () => {
    try {
      const devList = await devicesApi.listDevices({ limit: 100 });
      setDevices(devList);
    } catch (e) {
      console.error('Error fetching devices:', e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDevices();
  }, []);

  const handleToggleStatus = async (deviceId: string, currentStatus: DeviceStatus) => {
    const nextStatus = currentStatus === 'ACTIVE' ? 'REVOKED' : 'ACTIVE';
    try {
      await devicesApi.updateDeviceStatus(deviceId, nextStatus);
      success(
        nextStatus === 'REVOKED' ? 'Device Suspended' : 'Device Activated',
        `Device ${deviceId} status changed to ${nextStatus}.`
      );
      fetchDevices();
    } catch (err: unknown) {
      toastError('Status Update Failed', err instanceof Error ? err.message : 'Status update failed.');
    }
  };

  if (loading) {
    return <LoadingSpinner message="Loading IoT Devices..." size="lg" />;
  }

  return (
    <div className="space-y-6">
      {/* Top Banner */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 glass-panel p-6 rounded-3xl">
        <div className="flex items-center gap-3.5">
          <div className="p-3 rounded-2xl bg-cyan-500/15 border border-cyan-500/30 text-cyan-400">
            <Cpu className="w-6 h-6" />
          </div>
          <div>
            <h2 className="text-xl font-bold text-slate-100 tracking-tight">IoT Field Devices</h2>
            <p className="text-xs text-slate-400 mt-0.5 max-w-2xl">
              Canopy weather stations, soil moisture nodes, and telemetry transmitters across forest plots.
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2.5">
          <button
            type="button"
            onClick={fetchDevices}
            className="p-2.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300 transition-colors"
            title="Refresh Devices"
          >
            <RefreshCw className="w-4 h-4" />
          </button>

          {canManage && (
            <button
              type="button"
              onClick={() => setIsRegisterOpen(true)}
              className="px-4 py-2.5 rounded-xl text-xs font-semibold bg-cyan-500 hover:bg-cyan-600 text-slate-950 transition-all shadow-glow-cyan flex items-center gap-1.5 font-sans"
            >
              <Plus className="w-4 h-4" />
              <span>Add Device</span>
            </button>
          )}
        </div>
      </div>

      {/* Hardware Table */}
      <DeviceTable
        devices={devices}
        onToggleStatus={handleToggleStatus}
        onSimulateTelemetry={(dev) => setSimulatorDevice(dev)}
      />

      {/* Register Modal */}
      <DeviceRegisterModal
        isOpen={isRegisterOpen}
        onClose={() => setIsRegisterOpen(false)}
        onDeviceRegistered={fetchDevices}
      />

      {/* Ingestion & Simulation Modal */}
      <DeviceSimulatorModal
        isOpen={!!simulatorDevice}
        onClose={() => setSimulatorDevice(null)}
        device={simulatorDevice}
        onIngestSuccess={fetchDevices}
      />
    </div>
  );
};
