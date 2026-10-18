import React, { useState, useEffect } from 'react';
import { dashboardApi } from '../api/dashboard';
import { treesApi } from '../api/trees';
import { satelliteApi } from '../api/satellite';
import {
  GISMapLayerResponse,
  Tree,
  AerialPresetItem,
  AerialDetectResponse,
} from '../types';
import { GoogleMapsGPSView } from '../components/map/GoogleMapsGPSView';
import { TreeDetailDrawer } from '../components/trees/TreeDetailDrawer';
import { AssignTreeIdModal, AssignTarget } from '../components/trees/AssignTreeIdModal';
import { useToast } from '../context/ToastContext';
import { getApiErrorMessage } from '../utils/apiError';
import { DEFAULT_MAP_CENTER } from '../utils/geoUtils';
import {
  MapPin,
  Layers,
  RefreshCw,
  X,
  Radio,
  Upload,
  Sparkles,
  Plane,
  FileImage,
  CheckCircle2,
} from 'lucide-react';

export const MapPage: React.FC = () => {
  const { success, error: toastError } = useToast();
  const [mapData, setMapData] = useState<GISMapLayerResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [selectedTree, setSelectedTree] = useState<Tree | null>(null);
  const [highlightedTreeUid, setHighlightedTreeUid] = useState<string | null>(null);
  const [assignTarget, setAssignTarget] = useState<AssignTarget | null>(null);
  const [assignOpen, setAssignOpen] = useState(false);

  // ========================================================
  // 🛰️ AI AERIAL DRONE RADAR SCANNER STATE (Coordinate Attention YOLOv5s)
  // ========================================================
  const [showAerialModal, setShowAerialModal] = useState(false);
  const [aerialPresets, setAerialPresets] = useState<AerialPresetItem[]>([]);
  const [selectedPresetId, setSelectedPresetId] = useState<string>('shivamogga_plantation');
  const [aerialScanTab, setAerialScanTab] = useState<'preset' | 'upload'>('preset');
  const [aerialConfThreshold, setAerialConfThreshold] = useState<number>(0.50);
  const [uploadedBase64, setUploadedBase64] = useState<string | null>(null);
  const [uploadedFileName, setUploadedFileName] = useState<string | null>(null);
  const [uploadedPreview, setUploadedPreview] = useState<string | null>(null);
  const [scanningAerial, setScanningAerial] = useState(false);
  const [aerialScanData, setAerialScanData] = useState<AerialDetectResponse | null>(null);

  const fetchMapLayers = async () => {
    try {
      const layer = await dashboardApi.getMapLayer();
      setMapData(layer);
    } catch (e) {
      console.error('Map layer load failed:', e);
      toastError('Map layers failed', getApiErrorMessage(e, 'Could not load GIS radar layers.'));
    } finally {
      setLoading(false);
    }

    try {
      const presetsRes = await satelliteApi.getAerialPresets().catch(() => ({ presets: [] }));
      if (presetsRes.presets && presetsRes.presets.length > 0) {
        setAerialPresets(presetsRes.presets);
      }
    } catch (e) {
      console.error('Presets load failed:', e);
    }
  };

  useEffect(() => {
    fetchMapLayers();
  }, []);

  const handleSelectTreeByUid = async (treeUid: string) => {
    try {
      const tree = await treesApi.getTree(treeUid);
      setSelectedTree(tree);
      setHighlightedTreeUid(treeUid);
    } catch (e) {
      console.error('Tree detail fetch failed:', e);
    }
  };

  // Handle Drone Image File Selection
  const handleImageFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setUploadedFileName(file.name);
    const reader = new FileReader();
    reader.onload = (event) => {
      const base64String = event.target?.result as string;
      setUploadedBase64(base64String);
      setUploadedPreview(base64String);
    };
    reader.readAsDataURL(file);
  };

  // Run AI Drone Radar Detection (Coordinate Attention YOLOv5s)
  const handleRunAerialDetection = async () => {
    setScanningAerial(true);
    try {
      let result: AerialDetectResponse;
      if (aerialScanTab === 'upload' && uploadedBase64) {
        result = await satelliteApi.detectAerialCanopies({
          image_base64: uploadedBase64,
          confidence_threshold: aerialConfThreshold,
          center_lat: DEFAULT_MAP_CENTER.latitude,
          center_lon: DEFAULT_MAP_CENTER.longitude,
          ground_sampling_distance_cm: 3.5,
        });
      } else {
        result = await satelliteApi.detectAerialCanopies({
          preset_id: selectedPresetId,
          confidence_threshold: aerialConfThreshold,
        });
      }

      setAerialScanData(result);
      setShowAerialModal(false);
      success(
        'AI Drone Radar Detection Active',
        `Localized ${result.sandalwood_count} Sandalwood crowns (${result.estimated_sandalwood_biomass_kg} kg biomass) via Coordinate Attention YOLOv5s!`
      );
    } catch (err: unknown) {
      toastError(
        'Aerial Detection Failed',
        err instanceof Error ? err.message : 'Deep learning crown detection failed.'
      );
    } finally {
      setScanningAerial(false);
    }
  };

  return (
    <div className="h-[calc(100vh-5.5rem)] flex flex-col font-sans">
      {/* Main Unified Map Console — basemap mounts immediately; data fills in */}
      <div className="flex-1 w-full h-full min-h-[500px] rounded-2xl overflow-hidden shadow-2xl relative">
        <GoogleMapsGPSView
          mapData={mapData}
          onSelectTree={handleSelectTreeByUid}
          onAssignDetection={(target) => {
            setAssignTarget(target);
            setAssignOpen(true);
          }}
          highlightedTreeUid={highlightedTreeUid}
          aerialScanData={aerialScanData}
          onClearAerialScan={() => setAerialScanData(null)}
          onOpenAerialScanner={() => setShowAerialModal(true)}
        />
        {loading && (
          <div className="absolute inset-0 z-[500] pointer-events-none flex items-start justify-center pt-16">
            <div className="pointer-events-none px-4 py-2 rounded-xl bg-slate-950/80 border border-slate-700/80 backdrop-blur-md text-xs font-mono text-emerald-300 shadow-lg">
              Loading GIS radar layers…
            </div>
          </div>
        )}
      </div>

      <AssignTreeIdModal
        isOpen={assignOpen}
        onClose={() => {
          setAssignOpen(false);
          setAssignTarget(null);
        }}
        target={assignTarget}
        onAssigned={() => fetchMapLayers()}
      />


      {/* 🛰️ MODAL: AI AERIAL DRONE RADAR SCANNER (Coordinate Attention YOLOv5s) */}
      {showAerialModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-sm animate-in fade-in">
          <div className="w-full max-w-md bg-[#111723] border border-slate-700/80 rounded-2xl p-5 shadow-2xl space-y-4">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <div className="flex items-center gap-2 text-slate-100 font-semibold text-sm">
                <Radio className="w-4 h-4 text-emerald-400 animate-pulse" />
                <span>AI Aerial Drone Radar Scanner</span>
              </div>
              <button
                type="button"
                onClick={() => setShowAerialModal(false)}
                className="p-1 text-slate-400 hover:text-white rounded-lg hover:bg-slate-800 transition-colors"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            {/* Sub-header with Architecture Badge */}
            <div className="p-2.5 rounded-xl bg-emerald-950/40 border border-emerald-800/40 flex items-center justify-between text-[11px] text-emerald-300">
              <span className="font-mono flex items-center gap-1.5">
                <Sparkles className="w-3.5 h-3.5 text-emerald-400" />
                {aerialScanTab === 'preset' ? 'Preset scenes:' : 'Upload scan:'}
              </span>
              <span className="font-bold font-mono px-2 py-0.5 rounded bg-emerald-900/60 border border-emerald-600/50">
                {aerialScanTab === 'preset'
                  ? 'SIMULATED layout'
                  : 'YOLO weights, or a simulated fallback'}
              </span>
            </div>

            {/* Mode Switch Tabs */}
            <div className="flex items-center bg-slate-900 p-1 rounded-xl border border-slate-800 text-xs">
              <button
                type="button"
                onClick={() => setAerialScanTab('preset')}
                className={`flex-1 py-1.5 rounded-lg flex items-center justify-center gap-1.5 transition-all font-medium ${
                  aerialScanTab === 'preset'
                    ? 'bg-emerald-600 text-white font-bold shadow-md'
                    : 'text-slate-400 hover:text-slate-200'
                }`}
              >
                <Plane className="w-3.5 h-3.5" />
                <span>UAV Flight Presets</span>
              </button>
              <button
                type="button"
                onClick={() => setAerialScanTab('upload')}
                className={`flex-1 py-1.5 rounded-lg flex items-center justify-center gap-1.5 transition-all font-medium ${
                  aerialScanTab === 'upload'
                    ? 'bg-emerald-600 text-white font-bold shadow-md'
                    : 'text-slate-400 hover:text-slate-200'
                }`}
              >
                <Upload className="w-3.5 h-3.5" />
                <span>Upload Drone Photo</span>
              </button>
            </div>

            {/* TAB 1: PRESET UAV FLIGHTS */}
            {aerialScanTab === 'preset' && (
              <div className="space-y-2 text-xs">
                <label className="block text-[11px] text-slate-400">Select Calibrated Drone Flight Parcel:</label>
                <div className="space-y-1.5 max-h-48 overflow-y-auto">
                  {aerialPresets.length > 0 ? (
                    aerialPresets.map((preset) => (
                      <div
                        key={preset.id}
                        onClick={() => setSelectedPresetId(preset.id)}
                        className={`p-2.5 rounded-xl border cursor-pointer transition-all flex items-center justify-between ${
                          selectedPresetId === preset.id
                            ? 'bg-emerald-950/60 border-emerald-500 text-slate-100'
                            : 'bg-slate-900 border-slate-800 hover:border-slate-700 text-slate-300'
                        }`}
                      >
                        <div className="space-y-0.5">
                          <h4 className="font-semibold text-xs">{preset.title.split('(')[0]}</h4>
                          <p className="text-[10px] text-slate-400 font-mono">{preset.location.split('(')[0]}</p>
                          <div className="flex items-center gap-2 text-[10px] text-emerald-400 font-mono">
                            <span>Altitude: {preset.flight_altitude_m}m</span>
                            <span>&bull;</span>
                            <span>GSD: {preset.ground_sampling_distance_cm}cm</span>
                          </div>
                        </div>
                        <div className="text-right">
                          <span className="text-xs font-mono font-bold text-emerald-300">
                            {preset.sandalwood_count} Trees
                          </span>
                        </div>
                      </div>
                    ))
                  ) : (
                    <div className="p-3 text-center text-slate-400 bg-slate-900 rounded-xl">
                      Shivamogga Reserve (UAV 4K Flight Block)
                    </div>
                  )}
                </div>
              </div>
            )}

            {/* TAB 2: UPLOAD TOP-DOWN ORTHOMOSAIC */}
            {aerialScanTab === 'upload' && (
              <div className="space-y-3 text-xs">
                <label className="block text-[11px] text-slate-400">Upload Top-Down Drone/Aerial Orthomosaic Image:</label>
                <div className="border-2 border-dashed border-slate-700 hover:border-emerald-500/80 rounded-xl p-4 text-center cursor-pointer transition-colors bg-slate-900/50">
                  <input
                    type="file"
                    accept="image/*"
                    onChange={handleImageFileChange}
                    className="hidden"
                    id="drone-upload-file"
                  />
                  <label htmlFor="drone-upload-file" className="cursor-pointer flex flex-col items-center gap-2">
                    {uploadedPreview ? (
                      <div className="space-y-2">
                        <img
                          src={uploadedPreview}
                          alt="Drone Orthomosaic Preview"
                          className="w-full h-28 object-cover rounded-lg border border-slate-700"
                        />
                        <div className="flex items-center justify-center gap-1.5 text-[11px] text-emerald-400 font-mono">
                          <CheckCircle2 className="w-3.5 h-3.5" />
                          <span>{uploadedFileName}</span>
                        </div>
                      </div>
                    ) : (
                      <>
                        <FileImage className="w-8 h-8 text-slate-500" />
                        <span className="text-xs text-slate-300 font-medium">Click or Drag &amp; Drop drone image (.jpg, .png)</span>
                        <span className="text-[10px] text-slate-500 font-mono">Processes via PyTorch Coordinate Attention Engine</span>
                      </>
                    )}
                  </label>
                </div>
              </div>
            )}

            {/* Confidence Threshold Slider */}
            <div className="space-y-1 pt-1">
              <div className="flex items-center justify-between text-[11px] text-slate-400 font-mono">
                <span>AI Confidence Threshold:</span>
                <span className="text-emerald-400 font-bold">{(aerialConfThreshold * 100).toFixed(0)}%</span>
              </div>
              <input
                type="range"
                min="0.30"
                max="0.90"
                step="0.05"
                value={aerialConfThreshold}
                onChange={(e) => setAerialConfThreshold(parseFloat(e.target.value))}
                className="w-full accent-emerald-500 cursor-pointer"
              />
            </div>

            {/* Action Buttons */}
            <div className="flex items-center gap-2 pt-2 border-t border-slate-800">
              <button
                type="button"
                disabled={scanningAerial || (aerialScanTab === 'upload' && !uploadedBase64)}
                onClick={handleRunAerialDetection}
                className="flex-1 py-2.5 rounded-xl bg-emerald-600 hover:bg-emerald-500 disabled:bg-slate-800 disabled:text-slate-500 text-white text-xs font-bold transition-all flex items-center justify-center gap-2 shadow-lg"
              >
                {scanningAerial ? (
                  <>
                    <RefreshCw className="w-4 h-4 animate-spin" />
                    <span>Running Neural Network Scan...</span>
                  </>
                ) : (
                  <>
                    <Radio className="w-4 h-4" />
                    <span>Run AI Drone Radar Detection</span>
                  </>
                )}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Tree Details Drawer */}
      <TreeDetailDrawer
        tree={selectedTree}
        onClose={() => {
          setSelectedTree(null);
          setHighlightedTreeUid(null);
        }}
        onTreeUpdated={() => fetchMapLayers()}
      />
    </div>
  );
};
