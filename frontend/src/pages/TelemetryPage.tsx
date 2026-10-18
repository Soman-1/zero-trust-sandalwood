import React, { useState, useEffect } from 'react';
import { measurementsApi } from '../api/measurements';
import {
  EnvironmentalMeasurement,
  MeasurementStatsResponse,
  IntegrityCheckResponse,
  IntegrityScanResponse,
} from '../types';
import { HashDisplay } from '../components/common/HashDisplay';
import { LoadingSpinner } from '../components/common/LoadingSpinner';
import { Modal } from '../components/common/Modal';
import { useToast } from '../context/ToastContext';
import {
  Activity,
  ShieldCheck,
  CheckCircle2,
  AlertTriangle,
  RefreshCw,
  Search,
  Scan,
  Thermometer,
  Droplets,
} from 'lucide-react';

export const TelemetryPage: React.FC = () => {
  const { success, error: toastError } = useToast();
  const [measurements, setMeasurements] = useState<EnvironmentalMeasurement[]>([]);
  const [stats, setStats] = useState<MeasurementStatsResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');
  const [anomalyFilter, setAnomalyFilter] = useState<string>('ALL');

  // Single record integrity check
  const [verifyingUid, setVerifyingUid] = useState<string | null>(null);
  const [singleCheckResult, setSingleCheckResult] = useState<IntegrityCheckResponse | null>(null);

  // Bulk audit scan modal
  const [isScanModalOpen, setIsScanModalOpen] = useState(false);
  const [scanning, setScanning] = useState(false);
  const [scanResult, setScanResult] = useState<IntegrityScanResponse | null>(null);

  const fetchData = async () => {
    try {
      const [measData, statsData] = await Promise.all([
        measurementsApi.listMeasurements({ limit: 100 }),
        measurementsApi.getStats(),
      ]);
      setMeasurements(measData.measurements || []);
      setStats(statsData);
    } catch (e) {
      console.error('Failed to load telemetry:', e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  const handleVerifySingle = async (uid: string) => {
    setVerifyingUid(uid);
    try {
      const res = await measurementsApi.verifyMeasurementIntegrity(uid);
      setSingleCheckResult(res);
      if (res.is_valid) {
        success('Verification Passed', 'Record integrity verified against cryptographic hash.');
      } else {
        toastError('Integrity Issue', res.message);
      }
    } catch (err: unknown) {
      toastError('Verification Failed', err instanceof Error ? err.message : 'Integrity verification failed.');
    } finally {
      setVerifyingUid(null);
    }
  };

  const handleRunAuditScan = async () => {
    setScanning(true);
    setScanResult(null);
    try {
      const res = await measurementsApi.scanIntegrityAudit({ limit: 1000 });
      setScanResult(res);
      if (res.status === 'HEALTHY') {
        success('Audit Complete', `All ${res.valid_records} records verified successfully in ${res.scan_duration_ms}ms.`);
      } else {
        toastError('Issues Detected', `${res.corrupted_records} discrepancies found.`);
      }
    } catch (err: unknown) {
      toastError('Audit Scan Failed', err instanceof Error ? err.message : 'Database audit scan failed.');
    } finally {
      setScanning(false);
    }
  };

  const filteredMeasurements = measurements.filter((m) => {
    const matchesSearch =
      m.measurement_uid.toLowerCase().includes(searchTerm.toLowerCase()) ||
      (m.tree_id && m.tree_id.toString().includes(searchTerm)) ||
      (m.region_id != null && m.region_id.toString().includes(searchTerm));

    const matchesAnomaly =
      anomalyFilter === 'ALL' ||
      (anomalyFilter === 'ANOMALY' && m.is_anomaly) ||
      (anomalyFilter === 'NORMAL' && !m.is_anomaly);

    return matchesSearch && matchesAnomaly;
  });

  if (loading) {
    return <LoadingSpinner message="Loading Sensor Telemetry..." size="lg" />;
  }

  return (
    <div className="space-y-6 font-sans">
      {/* Top Banner */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 glass-panel p-6 rounded-3xl">
        <div className="flex items-center gap-3.5">
          <div className="p-3 rounded-2xl bg-emerald-500/15 border border-emerald-500/30 text-emerald-400">
            <Activity className="w-6 h-6" />
          </div>
          <div>
            <h2 className="text-xl font-bold text-slate-100 tracking-tight">Environmental Telemetry</h2>
            <p className="text-xs text-slate-400 mt-0.5 max-w-2xl">
              Real-time microclimate sensors, soil moisture telemetry, and SHA-256 integrity verification.
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2.5">
          <button
            type="button"
            onClick={fetchData}
            className="p-2.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300 transition-colors"
            title="Refresh Telemetry"
          >
            <RefreshCw className="w-4 h-4" />
          </button>

          <button
            type="button"
            onClick={() => {
              setIsScanModalOpen(true);
              handleRunAuditScan();
            }}
            className="px-4 py-2.5 rounded-xl text-xs font-semibold bg-emerald-500 hover:bg-emerald-600 text-slate-950 transition-all shadow-glow-emerald flex items-center gap-1.5"
          >
            <Scan className="w-4 h-4" />
            <span>Audit Database</span>
          </button>
        </div>
      </div>

      {/* Stats Summary Cards */}
      {stats && (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="glass-panel p-4 rounded-2xl space-y-2">
            <div className="flex items-center justify-between text-xs text-rose-300">
              <span className="flex items-center gap-1.5 font-semibold">
                <Thermometer className="w-4 h-4 text-rose-400" />
                <span>Ambient Temperature</span>
              </span>
              <span className="text-slate-400 text-[11px] font-mono">Avg: {stats.temperature.avg.toFixed(1)}°C</span>
            </div>
            <div className="flex items-baseline justify-between text-xs pt-1 border-t border-slate-800/80 font-mono">
              <span className="text-slate-400 font-sans">Min: <strong className="text-slate-200">{stats.temperature.min}°C</strong></span>
              <span className="text-slate-400 font-sans">Max: <strong className="text-rose-400">{stats.temperature.max}°C</strong></span>
            </div>
          </div>

          <div className="glass-panel p-4 rounded-2xl space-y-2">
            <div className="flex items-center justify-between text-xs text-cyan-300">
              <span className="flex items-center gap-1.5 font-semibold">
                <Droplets className="w-4 h-4 text-cyan-400" />
                <span>Air Humidity</span>
              </span>
              <span className="text-slate-400 text-[11px] font-mono">Avg: {stats.humidity.avg.toFixed(1)}%</span>
            </div>
            <div className="flex items-baseline justify-between text-xs pt-1 border-t border-slate-800/80 font-mono">
              <span className="text-slate-400 font-sans">Min: <strong className="text-slate-200">{stats.humidity.min}%</strong></span>
              <span className="text-slate-400 font-sans">Max: <strong className="text-cyan-400">{stats.humidity.max}%</strong></span>
            </div>
          </div>

          <div className="glass-panel p-4 rounded-2xl space-y-2">
            <div className="flex items-center justify-between text-xs text-emerald-300">
              <span className="flex items-center gap-1.5 font-semibold">
                <Droplets className="w-4 h-4 text-emerald-400" />
                <span>Soil Moisture</span>
              </span>
              <span className="text-slate-400 text-[11px] font-mono">Avg: {stats.soil_moisture.avg.toFixed(1)}%</span>
            </div>
            <div className="flex items-baseline justify-between text-xs pt-1 border-t border-slate-800/80 font-mono">
              <span className="text-slate-400 font-sans">Min: <strong className="text-slate-200">{stats.soil_moisture.min}%</strong></span>
              <span className="text-slate-400 font-sans">Max: <strong className="text-emerald-400">{stats.soil_moisture.max}%</strong></span>
            </div>
          </div>
        </div>
      )}

      {/* Telemetry Table */}
      <div className="glass-panel rounded-2xl overflow-hidden space-y-3">
        {/* Table Search & Filters */}
        <div className="p-4 border-b border-slate-800 flex flex-col sm:flex-row items-center justify-between gap-3">
          <div className="relative w-full sm:w-80">
            <Search className="w-4 h-4 text-slate-400 absolute left-3.5 top-1/2 -translate-y-1/2" />
            <input
              type="text"
              placeholder="Search by UID, tree, region..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="w-full pl-9 pr-4 py-2 bg-slate-950/80 border border-slate-700/80 rounded-xl text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:border-emerald-500"
            />
          </div>

          <div className="flex items-center gap-1.5">
            <button
              type="button"
              onClick={() => setAnomalyFilter('ALL')}
              className={`px-3 py-1.5 rounded-lg text-xs font-semibold ${
                anomalyFilter === 'ALL'
                  ? 'bg-emerald-500 text-slate-950 font-bold'
                  : 'bg-slate-900 text-slate-400 hover:text-slate-200 border border-slate-800'
              }`}
            >
              All Readings
            </button>
            <button
              type="button"
              onClick={() => setAnomalyFilter('ANOMALY')}
              className={`px-3 py-1.5 rounded-lg text-xs font-semibold ${
                anomalyFilter === 'ANOMALY'
                  ? 'bg-rose-500 text-white font-bold'
                  : 'bg-slate-900 text-slate-400 hover:text-slate-200 border border-slate-800'
              }`}
            >
              Anomalies
            </button>
            <button
              type="button"
              onClick={() => setAnomalyFilter('NORMAL')}
              className={`px-3 py-1.5 rounded-lg text-xs font-semibold ${
                anomalyFilter === 'NORMAL'
                  ? 'bg-cyan-500 text-slate-950 font-bold'
                  : 'bg-slate-900 text-slate-400 hover:text-slate-200 border border-slate-800'
              }`}
            >
              Normal
            </button>
          </div>
        </div>

        {/* Table Body */}
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs text-slate-300">
            <thead className="bg-slate-950/60 text-[11px] uppercase tracking-wider text-slate-400 font-mono border-b border-slate-800">
              <tr>
                <th className="py-3 px-4 font-semibold">Measurement UID</th>
                <th className="py-3 px-4 font-semibold">Region / Tree</th>
                <th className="py-3 px-4 font-semibold">Temp</th>
                <th className="py-3 px-4 font-semibold">Humidity</th>
                <th className="py-3 px-4 font-semibold">Soil</th>
                <th className="py-3 px-4 font-semibold">Hash Seal</th>
                <th className="py-3 px-4 font-semibold text-right">Verification</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60 font-mono">
              {filteredMeasurements.length === 0 ? (
                <tr>
                  <td colSpan={7} className="py-8 text-center text-slate-500 font-sans">
                    No telemetry records found.
                  </td>
                </tr>
              ) : (
                filteredMeasurements.map((m) => (
                  <tr key={m.id} className="hover:bg-slate-800/40 transition-colors">
                    <td className="py-3 px-4 font-bold text-emerald-400">
                      <span>{m.measurement_uid.substring(0, 14)}...</span>
                      {m.is_anomaly && (
                        <span className="ml-2 px-1.5 py-0.2 rounded bg-rose-500/20 text-rose-300 border border-rose-500/40 text-[9px] uppercase font-sans font-bold">
                          ANOMALY
                        </span>
                      )}
                    </td>
                    <td className="py-3 px-4 text-slate-300 font-sans">
                      Region #{m.region_id} {m.tree_id ? `&bull; Tree #${m.tree_id}` : ''}
                    </td>
                    <td className="py-3 px-4 text-rose-300 font-semibold">{m.temperature}°C</td>
                    <td className="py-3 px-4 text-cyan-300 font-semibold">{m.humidity}%</td>
                    <td className="py-3 px-4 text-emerald-300 font-semibold">{m.soil_moisture}%</td>
                    <td className="py-3 px-4">
                      <HashDisplay hash={m.integrity_hash} length={8} />
                    </td>
                    <td className="py-3 px-4 text-right">
                      <button
                        type="button"
                        onClick={() => handleVerifySingle(m.measurement_uid)}
                        disabled={verifyingUid === m.measurement_uid}
                        className="px-2.5 py-1 rounded-lg bg-emerald-500/15 border border-emerald-500/30 hover:bg-emerald-500/30 text-emerald-300 text-[11px] font-sans font-semibold transition-colors inline-flex items-center gap-1"
                      >
                        <ShieldCheck className="w-3 h-3" />
                        <span>{verifyingUid === m.measurement_uid ? 'Checking...' : 'Verify Hash'}</span>
                      </button>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Bulk Database Integrity Audit Scan Modal */}
      <Modal
        isOpen={isScanModalOpen}
        onClose={() => setIsScanModalOpen(false)}
        title="Database Integrity Audit"
        subtitle="Verifies SHA-256 hashes across telemetry records to confirm tamper-free storage"
        maxWidth="lg"
      >
        <div className="space-y-4 font-mono text-xs">
          {scanning ? (
            <LoadingSpinner message="Validating SHA-256 Hashes Across Records..." />
          ) : scanResult ? (
            <div className="space-y-4 font-sans">
              <div
                className={`p-4 rounded-xl border flex items-center gap-3 ${
                  scanResult.status === 'HEALTHY'
                    ? 'bg-emerald-950/50 border-emerald-500/60 text-emerald-300'
                    : 'bg-rose-950/50 border-rose-500/60 text-rose-300'
                }`}
              >
                {scanResult.status === 'HEALTHY' ? (
                  <CheckCircle2 className="w-6 h-6 text-emerald-400 flex-shrink-0" />
                ) : (
                  <AlertTriangle className="w-6 h-6 text-rose-400 flex-shrink-0" />
                )}
                <div>
                  <h4 className="font-bold text-sm">
                    {scanResult.status === 'HEALTHY'
                      ? 'ALL RECORDS VERIFIED INTACT'
                      : 'INTEGRITY DISCREPANCY DETECTED'}
                  </h4>
                  <p className="text-[11px] opacity-90 mt-0.5">
                    Scanned {scanResult.total_scanned} records in {scanResult.scan_duration_ms}ms with 0 discrepancies.
                  </p>
                </div>
              </div>

              <div className="grid grid-cols-3 gap-3 text-center font-mono">
                <div className="p-3 bg-slate-950 rounded-xl border border-slate-800">
                  <span className="text-[10px] text-slate-500 block font-sans">Scanned</span>
                  <span className="font-bold text-slate-100 text-sm">{scanResult.total_scanned}</span>
                </div>
                <div className="p-3 bg-slate-950 rounded-xl border border-slate-800">
                  <span className="text-[10px] text-slate-500 block font-sans">Valid</span>
                  <span className="font-bold text-emerald-400 text-sm">{scanResult.valid_records}</span>
                </div>
                <div className="p-3 bg-slate-950 rounded-xl border border-slate-800">
                  <span className="text-[10px] text-slate-500 block font-sans">Corrupted</span>
                  <span className="font-bold text-rose-400 text-sm">{scanResult.corrupted_records}</span>
                </div>
              </div>

              <div className="flex justify-end pt-2">
                <button
                  type="button"
                  onClick={() => setIsScanModalOpen(false)}
                  className="px-5 py-2 rounded-xl text-xs font-semibold bg-emerald-500 hover:bg-emerald-600 text-slate-950 transition-colors"
                >
                  Done
                </button>
              </div>
            </div>
          ) : null}
        </div>
      </Modal>

      {/* Single Verification Feedback Modal */}
      {singleCheckResult && (
        <Modal
          isOpen={!!singleCheckResult}
          onClose={() => setSingleCheckResult(null)}
          title="Hash Verification"
          subtitle={`UID: ${singleCheckResult.measurement_uid}`}
          maxWidth="md"
        >
          <div className="space-y-4 font-mono text-xs">
            <div
              className={`p-3.5 rounded-xl border flex items-center gap-3 font-sans ${
                singleCheckResult.is_valid
                  ? 'bg-emerald-950/60 border-emerald-500/60 text-emerald-300'
                  : 'bg-rose-950/60 border-rose-500/60 text-rose-300'
              }`}
            >
              {singleCheckResult.is_valid ? (
                <CheckCircle2 className="w-5 h-5 text-emerald-400 flex-shrink-0" />
              ) : (
                <AlertTriangle className="w-5 h-5 text-rose-400 flex-shrink-0" />
              )}
              <span className="text-xs">{singleCheckResult.message}</span>
            </div>

            <div className="space-y-2.5 p-3 rounded-xl bg-slate-950 border border-slate-800 text-[11px]">
              <div>
                <span className="text-slate-500 block font-sans">Stored Hash:</span>
                <HashDisplay hash={singleCheckResult.stored_hash} length={12} />
              </div>
              <div>
                <span className="text-slate-500 block font-sans">Computed Hash:</span>
                <HashDisplay hash={singleCheckResult.computed_hash} length={12} />
              </div>
            </div>

            <div className="flex justify-end pt-2">
              <button
                type="button"
                onClick={() => setSingleCheckResult(null)}
                className="px-4 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-semibold"
              >
                Close
              </button>
            </div>
          </div>
        </Modal>
      )}
    </div>
  );
};
