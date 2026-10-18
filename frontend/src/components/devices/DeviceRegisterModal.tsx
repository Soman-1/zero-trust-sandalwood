import React, { useState } from 'react';
import { Modal } from '../common/Modal';
import { DeviceType } from '../../types';
import { devicesApi } from '../../api/devices';
import { useToast } from '../../context/ToastContext';
import { getApiErrorMessage } from '../../utils/apiError';
import { Cpu, Key, Copy, Check, AlertTriangle, ShieldCheck } from 'lucide-react';

interface DeviceRegisterModalProps {
  isOpen: boolean;
  onClose: () => void;
  onDeviceRegistered: () => void;
}

export const DeviceRegisterModal: React.FC<DeviceRegisterModalProps> = ({
  isOpen,
  onClose,
  onDeviceRegistered,
}) => {
  const { success, error: toastError } = useToast();
  const [loading, setLoading] = useState(false);
  const [generatedKey, setGeneratedKey] = useState<string | null>(null);
  const [registeredDeviceId, setRegisteredDeviceId] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);

  const [formData, setFormData] = useState({
    device_id: `DEV-KA-${Math.floor(1000 + Math.random() * 9000)}`,
    name: 'Sector Monitoring Telemetry Node',
    device_type: 'STATIONARY_NODE' as DeviceType,
    initial_latitude: 13.935,
    initial_longitude: 75.565,
  });

  const handleCopyKey = () => {
    if (generatedKey) {
      navigator.clipboard.writeText(generatedKey);
      setCopied(true);
      success('API Key Copied', 'Store key securely in device hardware EEPROM/firmware.');
      setTimeout(() => setCopied(false), 2000);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);

    try {
      const resp = await devicesApi.registerDevice({
        device_id: formData.device_id,
        name: formData.name,
        device_type: formData.device_type,
        initial_latitude: Number(formData.initial_latitude),
        initial_longitude: Number(formData.initial_longitude),
      });

      setGeneratedKey(resp.api_key);
      setRegisteredDeviceId(resp.device.device_id);
      success('Device Registered', 'Cryptographic API Key generated.');
      onDeviceRegistered();
    } catch (err: unknown) {
      toastError('Registration Failed', getApiErrorMessage(err));
    } finally {
      setLoading(false);
    }
  };

  const handleFinish = () => {
    setGeneratedKey(null);
    setRegisteredDeviceId(null);
    onClose();
  };

  return (
    <Modal
      isOpen={isOpen}
      onClose={handleFinish}
      title={generatedKey ? 'Zero Trust Hardware Key Issued' : 'Provision IoT Field Hardware'}
      subtitle="HMAC authentication for field telemetry nodes"
      maxWidth="lg"
    >
      {generatedKey ? (
        <div className="space-y-4">
          <div className="p-4 rounded-xl bg-amber-500/10 border border-amber-500/30 flex items-start gap-3">
            <AlertTriangle className="w-5 h-5 text-amber-400 flex-shrink-0 mt-0.5" />
            <div className="text-xs text-amber-200">
              <p className="font-bold">One-Time API Key Display</p>
              <p className="mt-0.5 text-amber-300/80">
                This cryptographic token is only displayed once. Flash it into the IoT microcontroller firmware (ESP32 / LoRaWAN Node).
              </p>
            </div>
          </div>

          <div className="p-4 rounded-xl bg-slate-950 border border-slate-800 space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-xs font-mono text-slate-400">Device ID: {registeredDeviceId}</span>
              <span className="text-[10px] uppercase font-mono px-2 py-0.5 rounded bg-emerald-500/20 text-emerald-300">
                ACTIVE
              </span>
            </div>

            <div className="flex items-center gap-2 p-2.5 rounded-lg bg-slate-900 border border-slate-700">
              <Key className="w-4 h-4 text-emerald-400 flex-shrink-0" />
              <span className="font-mono text-xs text-emerald-300 break-all select-all flex-1">
                {generatedKey}
              </span>
              <button
                onClick={handleCopyKey}
                className="p-1.5 rounded-md bg-slate-800 hover:bg-slate-700 text-slate-300 hover:text-white transition-colors"
                title="Copy API Key"
              >
                {copied ? <Check className="w-4 h-4 text-emerald-400" /> : <Copy className="w-4 h-4" />}
              </button>
            </div>
          </div>

          <div className="flex justify-end pt-2">
            <button
              onClick={handleFinish}
              className="px-5 py-2 rounded-xl text-xs font-bold bg-emerald-500 hover:bg-emerald-600 text-slate-950 transition-colors shadow-glow-emerald"
            >
              Done &amp; Close
            </button>
          </div>
        </div>
      ) : (
        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-semibold text-slate-300 mb-1">Hardware UID *</label>
              <input
                type="text"
                value={formData.device_id}
                onChange={(e) => setFormData({ ...formData, device_id: e.target.value })}
                className="w-full px-3 py-2 bg-slate-950/80 border border-slate-700 rounded-xl text-xs text-slate-200 font-mono focus:border-emerald-500"
                required
              />
            </div>
            <div>
              <label className="block text-xs font-semibold text-slate-300 mb-1">Device Type *</label>
              <select
                value={formData.device_type}
                onChange={(e) => setFormData({ ...formData, device_type: e.target.value as DeviceType })}
                className="w-full px-3 py-2 bg-slate-950/80 border border-slate-700 rounded-xl text-xs text-slate-200 focus:border-emerald-500"
              >
                <option value="STATIONARY_NODE">Stationary Solar Node</option>
                <option value="MOBILE_SURVEYOR">Mobile Drone / Handheld</option>
              </select>
            </div>
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-300 mb-1">Friendly Name *</label>
            <input
              type="text"
              value={formData.name}
              onChange={(e) => setFormData({ ...formData, name: e.target.value })}
              className="w-full px-3 py-2 bg-slate-950/80 border border-slate-700 rounded-xl text-xs text-slate-200 focus:border-emerald-500"
              required
            />
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs text-slate-400 mb-1">Initial Latitude</label>
              <input
                type="number"
                step="0.0001"
                value={formData.initial_latitude}
                onChange={(e) => setFormData({ ...formData, initial_latitude: parseFloat(e.target.value) })}
                className="w-full px-3 py-1.5 bg-slate-950/80 border border-slate-700 rounded-xl text-xs text-slate-200 font-mono"
              />
            </div>
            <div>
              <label className="block text-xs text-slate-400 mb-1">Initial Longitude</label>
              <input
                type="number"
                step="0.0001"
                value={formData.initial_longitude}
                onChange={(e) => setFormData({ ...formData, initial_longitude: parseFloat(e.target.value) })}
                className="w-full px-3 py-1.5 bg-slate-950/80 border border-slate-700 rounded-xl text-xs text-slate-200 font-mono"
              />
            </div>
          </div>

          <div className="flex items-center justify-end gap-3 pt-3 border-t border-slate-800">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 rounded-xl text-xs font-semibold text-slate-400 hover:text-slate-200 bg-slate-800 hover:bg-slate-700 transition-colors"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={loading}
              className="px-5 py-2 rounded-xl text-xs font-bold bg-cyan-500 hover:bg-cyan-600 text-slate-950 transition-colors shadow-glow-cyan flex items-center gap-1.5"
            >
              <Cpu className="w-4 h-4" />
              <span>{loading ? 'Issuing Hardware Key...' : 'Provision IoT Device'}</span>
            </button>
          </div>
        </form>
      )}
    </Modal>
  );
};
