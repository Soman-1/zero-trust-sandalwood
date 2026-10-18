import React, { useState } from 'react';
import { Modal } from '../common/Modal';
import { Device } from '../../types';
import { measurementsApi } from '../../api/measurements';
import { useToast } from '../../context/ToastContext';
import { DEFAULT_MAP_CENTER } from '../../utils/geoUtils';
import { Play, ShieldAlert, CheckCircle2, AlertTriangle, Flame, Snowflake } from 'lucide-react';

interface DeviceSimulatorModalProps {
  isOpen: boolean;
  onClose: () => void;
  device: Device | null;
  onIngestSuccess: () => void;
}

export const DeviceSimulatorModal: React.FC<DeviceSimulatorModalProps> = ({
  isOpen,
  onClose,
  device,
  onIngestSuccess,
}) => {
  const { success, error: toastError } = useToast();
  const [loading, setLoading] = useState(false);
  const [apiKey, setApiKey] = useState('');
  const [ingestResponse, setIngestResponse] = useState<any>(null);

  const devicePosition = {
    latitude: device?.last_latitude ?? DEFAULT_MAP_CENTER.latitude,
    longitude: device?.last_longitude ?? DEFAULT_MAP_CENTER.longitude,
  };

  const [telemetry, setTelemetry] = useState({
    tree_id: 'KA-00001',
    ...devicePosition,
    temperature: 28.0,
    humidity: 65.0,
    soil_moisture: 50.0,
  });

  if (!device) return null;

  // Preset scenarios to demonstrate Zero Trust and AI Anomaly capabilities
  const applyScenario = (type: 'normal' | 'heat_anomaly' | 'physics_attack') => {
    if (type === 'normal') {
      setTelemetry({
        tree_id: 'KA-00001',
        ...devicePosition,
        temperature: 27.5,
        humidity: 68.0,
        soil_moisture: 52.0,
      });
    } else if (type === 'heat_anomaly') {
      setTelemetry({
        tree_id: 'KA-00001',
        ...devicePosition,
        temperature: 46.5,
        humidity: 14.0,
        soil_moisture: 8.5,
      });
    } else if (type === 'physics_attack') {
      setTelemetry({
        tree_id: 'KA-00001',
        ...devicePosition,
        temperature: 150.0, // Impossible sensor temperature!
        humidity: 150.0,
        soil_moisture: -30.0,
      });
    }
  };

  const handleSimulate = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setIngestResponse(null);

    try {
      const res = await measurementsApi.ingestSingle(
        device.device_id,
        apiKey || 'demo-mock-key',
        {
          tree_id: telemetry.tree_id || undefined,
          latitude: Number(telemetry.latitude),
          longitude: Number(telemetry.longitude),
          temperature: Number(telemetry.temperature),
          humidity: Number(telemetry.humidity),
          soil_moisture: Number(telemetry.soil_moisture),
        }
      );

      setIngestResponse({ success: true, data: res });
      success('Telemetry Packet Ingested', `Measurement UID: ${res.measurement_uid}`);
      onIngestSuccess();
    } catch (err: any) {
      const errData = err.response?.data?.error || err.response?.data || { message: err.message };
      setIngestResponse({ success: false, error: errData });
      toastError('Zero Trust Rejection', errData.message || 'Validation failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title={`IoT Telemetry Simulator: ${device.device_id}`}
      subtitle="Test physical sensor constraints and AI anomaly detection"
      maxWidth="xl"
    >
      <div className="space-y-4">
        {/* Scenario Presets */}
        <div>
          <label className="block text-xs font-semibold text-slate-300 mb-1.5">
            Quick Attack / Test Scenarios:
          </label>
          <div className="grid grid-cols-3 gap-2">
            <button
              type="button"
              onClick={() => applyScenario('normal')}
              className="p-2 rounded-xl bg-emerald-950/40 border border-emerald-500/30 text-emerald-300 hover:bg-emerald-900/40 text-xs font-medium flex flex-col items-center gap-1 transition-colors"
            >
              <CheckCircle2 className="w-4 h-4 text-emerald-400" />
              <span>Normal Microclimate</span>
            </button>

            <button
              type="button"
              onClick={() => applyScenario('heat_anomaly')}
              className="p-2 rounded-xl bg-rose-950/40 border border-rose-500/30 text-rose-300 hover:bg-rose-900/40 text-xs font-medium flex flex-col items-center gap-1 transition-colors"
            >
              <Flame className="w-4 h-4 text-rose-400" />
              <span>Heat Stress (AI)</span>
            </button>

            <button
              type="button"
              onClick={() => applyScenario('physics_attack')}
              className="p-2 rounded-xl bg-purple-950/40 border border-purple-500/30 text-purple-300 hover:bg-purple-900/40 text-xs font-medium flex flex-col items-center gap-1 transition-colors"
            >
              <ShieldAlert className="w-4 h-4 text-purple-400" />
              <span>Sensor Bounds Attack</span>
            </button>
          </div>
        </div>

        {/* Input Form */}
        <form onSubmit={handleSimulate} className="space-y-3 font-mono text-xs">
          <div>
            <label className="block text-[11px] text-slate-400 mb-1">
              Device API Key Header (Optional for Admin simulation)
            </label>
            <input
              type="password"
              placeholder="Paste X-Device-Key or leave blank"
              value={apiKey}
              onChange={(e) => setApiKey(e.target.value)}
              className="w-full px-3 py-1.5 bg-slate-950 border border-slate-700 rounded-lg text-slate-200"
            />
          </div>

          <div>
            <div>
              <label className="block text-[11px] text-slate-400 mb-1">Tree UID (Optional)</label>
              <input
                type="text"
                value={telemetry.tree_id}
                onChange={(e) => setTelemetry({ ...telemetry, tree_id: e.target.value })}
                className="w-full px-3 py-1.5 bg-slate-950 border border-slate-700 rounded-lg text-slate-200"
              />
            </div>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-[11px] text-slate-400 mb-1">Simulated Latitude</label>
              <input
                type="number"
                step="0.0001"
                value={telemetry.latitude}
                onChange={(e) => setTelemetry({ ...telemetry, latitude: parseFloat(e.target.value) })}
                className="w-full px-3 py-1.5 bg-slate-950 border border-slate-700 rounded-lg text-slate-200"
                required
              />
            </div>
            <div>
              <label className="block text-[11px] text-slate-400 mb-1">Simulated Longitude</label>
              <input
                type="number"
                step="0.0001"
                value={telemetry.longitude}
                onChange={(e) => setTelemetry({ ...telemetry, longitude: parseFloat(e.target.value) })}
                className="w-full px-3 py-1.5 bg-slate-950 border border-slate-700 rounded-lg text-slate-200"
                required
              />
            </div>
          </div>

          <div className="grid grid-cols-3 gap-3">
            <div>
              <label className="block text-[11px] text-rose-400 mb-1">Temp (°C)</label>
              <input
                type="number"
                step="0.1"
                value={telemetry.temperature}
                onChange={(e) => setTelemetry({ ...telemetry, temperature: parseFloat(e.target.value) })}
                className="w-full px-3 py-1.5 bg-slate-950 border border-slate-700 rounded-lg text-slate-200 text-center font-bold"
                required
              />
            </div>
            <div>
              <label className="block text-[11px] text-cyan-400 mb-1">Humidity (%)</label>
              <input
                type="number"
                step="0.1"
                value={telemetry.humidity}
                onChange={(e) => setTelemetry({ ...telemetry, humidity: parseFloat(e.target.value) })}
                className="w-full px-3 py-1.5 bg-slate-950 border border-slate-700 rounded-lg text-slate-200 text-center font-bold"
                required
              />
            </div>
            <div>
              <label className="block text-[11px] text-emerald-400 mb-1">Soil Moisture (%)</label>
              <input
                type="number"
                step="0.1"
                value={telemetry.soil_moisture}
                onChange={(e) => setTelemetry({ ...telemetry, soil_moisture: parseFloat(e.target.value) })}
                className="w-full px-3 py-1.5 bg-slate-950 border border-slate-700 rounded-lg text-slate-200 text-center font-bold"
                required
              />
            </div>
          </div>

          {/* Result Box */}
          {ingestResponse && (
            <div
              className={`p-3 rounded-xl border text-xs ${
                ingestResponse.success
                  ? 'bg-emerald-950/60 border-emerald-500/60 text-emerald-300'
                  : 'bg-rose-950/60 border-rose-500/60 text-rose-300'
              }`}
            >
              <div className="flex items-center gap-2 font-bold mb-1">
                {ingestResponse.success ? (
                  <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                ) : (
                  <ShieldAlert className="w-4 h-4 text-rose-400" />
                )}
                <span>
                  {ingestResponse.success
                    ? '201 CREATED: Telemetry Passed Zero Trust Verification'
                    : `Zero Trust Gate Rejection: ${ingestResponse.error?.code || 'SECURITY_POLICY_VIOLATION'}`}
                </span>
              </div>
              <p className="text-[11px] opacity-90">
                {ingestResponse.success
                  ? `Canonical SHA-256 seal computed and saved into SQLite/PostgreSQL ledger.`
                  : ingestResponse.error?.message || JSON.stringify(ingestResponse.error)}
              </p>
            </div>
          )}

          <div className="flex justify-end pt-2">
            <button
              type="submit"
              disabled={loading}
              className="px-5 py-2.5 rounded-xl text-xs font-bold bg-cyan-500 hover:bg-cyan-600 text-slate-950 transition-colors shadow-glow-cyan flex items-center gap-2"
            >
              <Play className="w-4 h-4" />
              <span>{loading ? 'Transmitting Ingestion Packet...' : 'Transmit Ingest Packet'}</span>
            </button>
          </div>
        </form>
      </div>
    </Modal>
  );
};
