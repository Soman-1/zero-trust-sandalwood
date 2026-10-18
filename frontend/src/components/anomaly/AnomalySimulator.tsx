import React, { useState, useEffect } from 'react';
import { anomalyApi } from '../../api/anomaly';
import { AnomalyEvaluateResponse, ModelStatusResponse } from '../../types';
import { useToast } from '../../context/ToastContext';
import { getApiErrorMessage } from '../../utils/apiError';
import { useAuth } from '../../context/AuthContext';
import {
  BrainCircuit,
  Sliders,
  Sparkles,
  ShieldCheck,
  AlertTriangle,
  RefreshCw,
  Gauge,
  Thermometer,
  Droplets,
} from 'lucide-react';

export const AnomalySimulator: React.FC = () => {
  const { isAdmin } = useAuth();
  const { success, error: toastError } = useToast();
  const [modelStatus, setModelStatus] = useState<ModelStatusResponse | null>(null);
  const [evaluating, setEvaluating] = useState(false);
  const [retraining, setRetraining] = useState(false);
  const [evaluationResult, setEvaluationResult] = useState<AnomalyEvaluateResponse | null>(null);

  const [inputs, setInputs] = useState({
    temperature: 28.0,
    humidity: 65.0,
    soil_moisture: 50.0,
  });

  const fetchModelStatus = async () => {
    try {
      const status = await anomalyApi.getStatus();
      setModelStatus(status);
    } catch (e) {
      console.error('Error fetching model status:', e);
    }
  };

  useEffect(() => {
    fetchModelStatus();
  }, []);

  const handleEvaluate = async () => {
    setEvaluating(true);
    try {
      const res = await anomalyApi.evaluate({
        temperature: Number(inputs.temperature),
        humidity: Number(inputs.humidity),
        soil_moisture: Number(inputs.soil_moisture),
      });
      setEvaluationResult(res);
      if (res.is_anomaly) {
        toastError('AI Anomaly Detected', res.interpretation);
      } else {
        success('Microclimate Normal', res.interpretation);
      }
    } catch (err: any) {
      toastError('Evaluation Failed', err.message);
    } finally {
      setEvaluating(false);
    }
  };

  const handleRetrain = async () => {
    setRetraining(true);
    try {
      const res = await anomalyApi.retrainModel(10);
      success('AI Model Retrained', res.message);
      await fetchModelStatus();
    } catch (err: unknown) {
      toastError('Retraining Note', getApiErrorMessage(err));
    } finally {
      setRetraining(false);
    }
  };

  return (
    <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
      {/* 1. Interactive Parameter Controls */}
      <div className="lg:col-span-2 glass-panel p-6 rounded-2xl space-y-6">
        <div className="flex items-center justify-between border-b border-slate-800 pb-4">
          <div>
            <h3 className="text-base font-bold text-slate-100 flex items-center gap-2">
              <Sliders className="w-5 h-5 text-emerald-400" />
              <span>Interactive Environmental AI Sandbox</span>
            </h3>
            <p className="text-xs text-slate-400 mt-0.5">
              Simulate microclimate variations to test the Isolation Forest decision boundary &amp; VPD calculation
            </p>
          </div>
        </div>

        {/* Sliders */}
        <div className="space-y-5">
          {/* Temperature */}
          <div className="space-y-2">
            <div className="flex items-center justify-between text-xs font-mono">
              <span className="text-slate-300 flex items-center gap-1.5 font-sans font-semibold">
                <Thermometer className="w-4 h-4 text-rose-400" />
                <span>Ambient Air Temperature</span>
              </span>
              <span className="font-bold text-rose-400 text-sm">{inputs.temperature}°C</span>
            </div>
            <input
              type="range"
              min="0"
              max="60"
              step="0.5"
              value={inputs.temperature}
              onChange={(e) => setInputs({ ...inputs, temperature: parseFloat(e.target.value) })}
              className="w-full h-2 bg-slate-800 rounded-lg appearance-none cursor-pointer accent-rose-500"
            />
            <div className="flex justify-between text-[10px] text-slate-500 font-mono">
              <span>0°C (Frost)</span>
              <span>25°C - 32°C (Optimal Sandalwood Belt)</span>
              <span>60°C (Extreme Heat)</span>
            </div>
          </div>

          {/* Relative Humidity */}
          <div className="space-y-2">
            <div className="flex items-center justify-between text-xs font-mono">
              <span className="text-slate-300 flex items-center gap-1.5 font-sans font-semibold">
                <Droplets className="w-4 h-4 text-cyan-400" />
                <span>Canopy Relative Humidity</span>
              </span>
              <span className="font-bold text-cyan-400 text-sm">{inputs.humidity}%</span>
            </div>
            <input
              type="range"
              min="5"
              max="100"
              step="1"
              value={inputs.humidity}
              onChange={(e) => setInputs({ ...inputs, humidity: parseFloat(e.target.value) })}
              className="w-full h-2 bg-slate-800 rounded-lg appearance-none cursor-pointer accent-cyan-500"
            />
            <div className="flex justify-between text-[10px] text-slate-500 font-mono">
              <span>5% (Arid Desiccation)</span>
              <span>60% - 75% (Ideal)</span>
              <span>100% (Saturated)</span>
            </div>
          </div>

          {/* Soil Moisture */}
          <div className="space-y-2">
            <div className="flex items-center justify-between text-xs font-mono">
              <span className="text-slate-300 flex items-center gap-1.5 font-sans font-semibold">
                <Droplets className="w-4 h-4 text-emerald-400" />
                <span>Volumetric Soil Moisture</span>
              </span>
              <span className="font-bold text-emerald-400 text-sm">{inputs.soil_moisture}%</span>
            </div>
            <input
              type="range"
              min="0"
              max="100"
              step="1"
              value={inputs.soil_moisture}
              onChange={(e) => setInputs({ ...inputs, soil_moisture: parseFloat(e.target.value) })}
              className="w-full h-2 bg-slate-800 rounded-lg appearance-none cursor-pointer accent-emerald-500"
            />
            <div className="flex justify-between text-[10px] text-slate-500 font-mono">
              <span>0% (Severe Drought)</span>
              <span>45% - 65% (Optimal)</span>
              <span>100% (Waterlogged)</span>
            </div>
          </div>
        </div>

        {/* Action Button */}
        <div className="flex items-center justify-between pt-4 border-t border-slate-800">
          <div className="flex items-center gap-2">
            <button
              onClick={() => setInputs({ temperature: 27.5, humidity: 68.0, soil_moisture: 52.0 })}
              className="px-3 py-1.5 rounded-lg text-xs font-medium bg-slate-800 hover:bg-slate-700 text-slate-300 transition-colors"
            >
              Reset Baseline
            </button>
            <button
              onClick={() => setInputs({ temperature: 47.0, humidity: 12.0, soil_moisture: 7.0 })}
              className="px-3 py-1.5 rounded-lg text-xs font-medium bg-rose-950/40 border border-rose-800/60 text-rose-300 hover:bg-rose-900/40 transition-colors"
            >
              Simulate Heat Stress
            </button>
          </div>

          <button
            onClick={handleEvaluate}
            disabled={evaluating}
            className="px-6 py-2.5 rounded-xl text-xs font-bold bg-emerald-500 hover:bg-emerald-600 text-slate-950 transition-colors shadow-glow-emerald flex items-center gap-2"
          >
            <Sparkles className="w-4 h-4" />
            <span>{evaluating ? 'Evaluating Isolation Forest...' : 'Run AI Evaluation'}</span>
          </button>
        </div>

        {/* AI Output Inspection Box */}
        {evaluationResult && (
          <div
            className={`p-5 rounded-2xl border transition-all ${
              evaluationResult.is_anomaly
                ? 'bg-rose-950/40 border-rose-500/60 shadow-glow-rose'
                : 'bg-emerald-950/40 border-emerald-500/60 shadow-glow-emerald'
            }`}
          >
            <div className="flex items-center justify-between mb-3">
              <div className="flex items-center gap-2">
                {evaluationResult.is_anomaly ? (
                  <AlertTriangle className="w-5 h-5 text-rose-400 animate-pulse" />
                ) : (
                  <ShieldCheck className="w-5 h-5 text-emerald-400" />
                )}
                <h4
                  className={`font-bold text-sm uppercase font-mono ${
                    evaluationResult.is_anomaly ? 'text-rose-300' : 'text-emerald-300'
                  }`}
                >
                  {evaluationResult.is_anomaly ? 'CRITICAL ANOMALY DETECTED' : 'MICROCLIMATE STABLE'}
                </h4>
              </div>
              <span className="text-xs font-mono px-2.5 py-1 rounded bg-slate-950 border border-slate-800 text-slate-300">
                Score: {evaluationResult.anomaly_score}
              </span>
            </div>

            <p className="text-xs text-slate-200 mb-4">{evaluationResult.interpretation}</p>

            {/* Feature Breakdown Grid */}
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 text-xs font-mono text-center">
              <div className="p-2 rounded-lg bg-slate-950/80 border border-slate-800">
                <span className="text-[10px] text-slate-500 block">VPD Index</span>
                <span className="font-bold text-amber-400">
                  {evaluationResult.details.vpd ? `${evaluationResult.details.vpd.toFixed(3)} kPa` : 'N/A'}
                </span>
              </div>
              <div className="p-2 rounded-lg bg-slate-950/80 border border-slate-800">
                <span className="text-[10px] text-slate-500 block">Raw Score</span>
                <span className="font-bold text-slate-300">
                  {evaluationResult.details.raw_decision_score
                    ? evaluationResult.details.raw_decision_score.toFixed(4)
                    : 'N/A'}
                </span>
              </div>
              <div className="p-2 rounded-lg bg-slate-950/80 border border-slate-800 col-span-2 text-left px-3">
                <span className="text-[10px] text-slate-500 block">Primary Stress Factor</span>
                <span className="font-bold text-slate-200 truncate block">
                  {evaluationResult.details.primary_factor || 'Baseline Equilibrium'}
                </span>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* 2. Model Diagnostics & Retraining Panel */}
      <div className="glass-panel p-6 rounded-2xl flex flex-col justify-between space-y-5">
        <div>
          <div className="flex items-center gap-2 mb-4 border-b border-slate-800 pb-3">
            <BrainCircuit className="w-5 h-5 text-purple-400" />
            <h4 className="text-sm font-bold text-slate-100">Isolation Forest AI Engine</h4>
          </div>

          <div className="space-y-3 font-mono text-xs">
            <div className="flex items-center justify-between p-2.5 rounded-lg bg-slate-950/60 border border-slate-800">
              <span className="text-slate-400 font-sans">Model Architecture</span>
              <span className="text-purple-300 font-bold">{modelStatus?.model_type || 'IsolationForest'}</span>
            </div>

            <div className="flex items-center justify-between p-2.5 rounded-lg bg-slate-950/60 border border-slate-800">
              <span className="text-slate-400 font-sans">Model Status</span>
              <span className="text-emerald-400 font-bold">
                {modelStatus?.is_fitted ? 'FITTED & ACTIVE' : 'AWAITING FIT'}
              </span>
            </div>

            <div className="flex items-center justify-between p-2.5 rounded-lg bg-slate-950/60 border border-slate-800">
              <span className="text-slate-400 font-sans">Trained Samples</span>
              <span className="text-cyan-400 font-bold">{modelStatus?.trained_samples || 0} Observations</span>
            </div>

            <div className="flex items-center justify-between p-2.5 rounded-lg bg-slate-950/60 border border-slate-800">
              <span className="text-slate-400 font-sans">Contamination Rate</span>
              <span className="text-amber-400 font-bold">
                {modelStatus?.contamination_rate ? `${(modelStatus.contamination_rate * 100).toFixed(1)}%` : '5.0%'}
              </span>
            </div>

            <div className="p-3 rounded-lg bg-slate-950/60 border border-slate-800 space-y-1.5">
              <span className="text-[10px] text-slate-500 uppercase tracking-wider block font-sans">
                Engineered Features
              </span>
              <div className="flex flex-wrap gap-1">
                {(modelStatus?.feature_names || ['temp', 'humidity', 'soil', 'vpd']).map((f) => (
                  <span
                    key={f}
                    className="px-2 py-0.5 rounded text-[10px] bg-purple-500/15 text-purple-300 border border-purple-500/30 font-mono"
                  >
                    {f}
                  </span>
                ))}
              </div>
            </div>
          </div>
        </div>

        {/* Retraining Trigger */}
        {isAdmin && (
          <div className="pt-4 border-t border-slate-800">
            <button
              onClick={handleRetrain}
              disabled={retraining}
              className="w-full py-2.5 px-4 rounded-xl text-xs font-bold bg-purple-600 hover:bg-purple-700 text-white transition-colors flex items-center justify-center gap-2 shadow-lg"
            >
              <RefreshCw className={`w-4 h-4 ${retraining ? 'animate-spin' : ''}`} />
              <span>{retraining ? 'Training on Historical Data...' : 'Retrain AI on Historical Telemetry'}</span>
            </button>
            <p className="text-[10px] text-slate-500 text-center mt-2">
              Fits the Isolation Forest on all verified historical observations in the database.
            </p>
          </div>
        )}
      </div>
    </div>
  );
};
