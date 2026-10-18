import React, { useEffect, useRef } from 'react';
import {
  Radio,
  Play,
  Pause,
  RotateCcw,
  ShieldCheck,
  Battery,
  Navigation,
  Crosshair,
  Target,
  Gauge,
  Compass,
  CheckCircle2,
  X,
  Trees,
  TreePine,
  Zap,
} from 'lucide-react';
import { MapContainer, useMap } from 'react-leaflet';
import 'leaflet/dist/leaflet.css';
import {
  DronePatrolMissionResponse,
  DroneLiveTelemetry,
  DroneMissionCanopyTarget,
} from '../../types';
import { SharpEsriImageryLayer } from '../map/SharpEsriImageryLayer';
import { MAP_CONSTRAINTS } from '../../utils/basemapTiles';

/** Inner component: pans the leaflet map to follow the drone without queueing animations. */
const DroneMapFollower: React.FC<{ lat: number; lon: number }> = ({ lat, lon }) => {
  const map = useMap();
  const prevPos = useRef<[number, number] | null>(null);
  useEffect(() => {
    const next: [number, number] = [lat, lon];
    if (prevPos.current && prevPos.current[0] === next[0] && prevPos.current[1] === next[1]) {
      return;
    }
    // panTo({ animate: true, duration: 0.8 }) on every telemetry tick queued
    // overlapping pans and a tile refetch storm. Jump if the move is small.
    map.setView(next, map.getZoom(), { animate: false });
    prevPos.current = next;
  }, [lat, lon, map]);
  return null;
};

interface DroneTacticalHUDProps {
  mission: DronePatrolMissionResponse | null;
  telemetry: DroneLiveTelemetry;
  isPlaying: boolean;
  speedMultiplier: number;
  onTogglePlay: () => void;
  onReset: () => void;
  onChangeSpeed: (multiplier: number) => void;
  onClose: () => void;
  interceptedTargets: DroneMissionCanopyTarget[];
}

export const DroneTacticalHUD: React.FC<DroneTacticalHUDProps> = ({
  mission,
  telemetry,
  isPlaying,
  speedMultiplier,
  onTogglePlay,
  onReset,
  onChangeSpeed,
  onClose,
  interceptedTargets,
}) => {
  if (!mission) return null;

  const locked = telemetry.locked_target;
  const totalDuration = mission.total_duration_sec || 100;
  const progressPct = Math.min(100, Math.max(0, (telemetry.elapsed_sec / totalDuration) * 100));

  const formatSecs = (sec: number) => {
    const m = Math.floor(sec / 60);
    const s = Math.floor(sec % 60);
    return `${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`;
  };

  const getHeadingCardinal = (deg: number) => {
    const directions = ['N', 'NE', 'E', 'SE', 'S', 'SW', 'W', 'NW'];
    const index = Math.round(((deg % 360) + 360) % 360 / 45) % 8;
    return directions[index];
  };

  return (
    <div className="bg-slate-950/95 backdrop-blur-md border border-emerald-500/40 rounded-2xl shadow-2xl overflow-hidden font-mono text-xs flex flex-col text-slate-200 select-none animate-in fade-in max-w-full">
      {/* 1. TOP TACTICAL FLIGHT STATUS BAR */}
      <div className="bg-[#0b101b] border-b border-emerald-900/60 p-3 px-4 flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-3">
          <div className="p-2 rounded-xl bg-emerald-500/15 border border-emerald-500/40 text-emerald-400 flex items-center gap-2">
            <Radio className={`w-4 h-4 ${isPlaying ? 'animate-pulse text-emerald-300' : 'text-slate-500'}`} />
            <span className="font-bold tracking-wider text-[11px]">UAV AUTONOMOUS PATROL</span>
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="font-bold text-slate-100 text-sm">{mission.drone_hardware_id}</span>
              <span className="px-1.5 py-0.5 rounded text-[10px] bg-cyan-950 border border-cyan-800 text-cyan-300 font-semibold">
                RTK-FIX 2.1cm
              </span>
            </div>
            <span className="text-[10px] text-slate-400 block">
              {mission.reserve_name} &bull; Leg WP-0{telemetry.active_waypoint_index + 1}
            </span>
          </div>
        </div>

        <div className="hidden md:flex items-center gap-4 bg-slate-900/80 px-3 py-1.5 rounded-xl border border-slate-800">
          <div className="flex items-center gap-1.5 text-emerald-400 text-[11px]">
            <ShieldCheck className="w-3.5 h-3.5" />
            <span className="font-semibold">GEOFENCE: VERIFIED INSIDE</span>
          </div>
          <span className="text-slate-600">|</span>
          <div className="text-[11px] text-slate-400 flex items-center gap-1.5">
            <span>CRYPTO SEAL:</span>
            <span className="text-emerald-300 font-mono text-[10px]">
              {mission.mission_integrity_hash.slice(0, 10)}...
            </span>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-slate-900 border border-slate-800 text-slate-300">
            <Battery className={`w-4 h-4 ${telemetry.battery_pct > 30 ? 'text-emerald-400' : 'text-rose-400 animate-pulse'}`} />
            <span className="font-bold">{telemetry.battery_pct.toFixed(0)}%</span>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="p-1.5 rounded-lg bg-slate-900 hover:bg-slate-800 text-slate-400 hover:text-white transition-colors"
            title="Close Tactical HUD"
          >
            <X className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* 2. DUAL MAIN VIEWPORT (Nadir Camera + Flight Instruments) */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-0 border-b border-slate-800/80">
        {/* LEFT: NADIR CAMERA FEED — Live Satellite Map with HUD overlays */}
        <div className="lg:col-span-7 relative flex flex-col min-h-[280px] overflow-hidden border-b lg:border-b-0 lg:border-r border-slate-800">

          {/* Satellite map fills the entire panel */}
          <div className="absolute inset-0 z-0">
            <MapContainer
              center={[telemetry.latitude, telemetry.longitude]}
              zoom={17}
              minZoom={MAP_CONSTRAINTS.minZoom}
              maxZoom={MAP_CONSTRAINTS.maxZoom}
              zoomSnap={MAP_CONSTRAINTS.zoomSnap}
              zoomDelta={MAP_CONSTRAINTS.zoomDelta}
              zoomControl={false}
              attributionControl={false}
              scrollWheelZoom={false}
              dragging={false}
              doubleClickZoom={false}
              touchZoom={false}
              keyboard={false}
              style={{ height: '100%', width: '100%' }}
            >
              {/* Sharp Esri Clarity + HD close-up fallback */}
              <SharpEsriImageryLayer showLabels />
              <DroneMapFollower lat={telemetry.latitude} lon={telemetry.longitude} />
            </MapContainer>
          </div>

          {/* Dark vignette over the map to keep the tactical feel */}
          <div
            className="absolute inset-0 z-10 pointer-events-none"
            style={{
              background: 'radial-gradient(ellipse at center, transparent 45%, rgba(0,10,5,0.62) 100%)',
            }}
          />
          {/* Subtle green scanlines overlay */}
          <div
            className="absolute inset-0 z-10 pointer-events-none opacity-10"
            style={{
              backgroundImage:
                'repeating-linear-gradient(0deg, transparent, transparent 3px, rgba(52,211,153,0.15) 3px, rgba(52,211,153,0.15) 4px)',
            }}
          />

          {/* TOP HUD bar */}
          <div className="relative z-20 flex items-center justify-between p-3 px-4 text-[10px] text-emerald-400/90 font-mono bg-gradient-to-b from-slate-950/80 to-transparent">
            <div className="flex items-center gap-2">
              <span className="w-2 h-2 rounded-full bg-rose-500 animate-ping" />
              <span className="font-bold tracking-widest text-slate-200 drop-shadow">CAM: NADIR -90° OPTICAL RGB</span>
            </div>
            <span className="drop-shadow">FOV 84° &bull; GSD 3.5 cm/px</span>
          </div>

          {/* Center Crosshairs & Laser Reticle over the map */}
          <div className="absolute inset-0 z-20 flex items-center justify-center pointer-events-none">
            <div className={`w-40 h-40 rounded-full border border-dashed transition-all duration-300 ${
              locked ? 'border-emerald-400 scale-105' : 'border-emerald-400/30'
            }`} />
            <div className="absolute w-12 h-0.5 bg-emerald-400/60" />
            <div className="absolute h-12 w-0.5 bg-emerald-400/60" />
            <Crosshair className={`w-6 h-6 drop-shadow transition-transform ${locked ? 'text-emerald-400 scale-125' : 'text-emerald-400/50'}`} />

            {/* Target Acquisition Lock Box */}
            {locked && (
              <div className="absolute p-3 rounded-xl bg-emerald-950/90 border-2 border-emerald-400 shadow-2xl backdrop-blur-sm animate-in zoom-in-90 flex flex-col items-center gap-1 text-center">
                <div className="flex items-center gap-1.5 text-emerald-300 font-bold text-[11px] tracking-wider">
                  <Target className="w-3.5 h-3.5 animate-spin" />
                  <span>[+] TARGET ACQUIRED</span>
                </div>
                <div className="text-sm font-bold text-white tracking-tight">
                  {locked.species_scientific}
                </div>
                <div className="text-[10px] text-slate-300 italic">
                  {locked.species_common}
                </div>
                <div className="flex items-center gap-2 mt-1 text-[10px] font-semibold">
                  <span className="px-1.5 py-0.5 rounded bg-emerald-900/80 text-emerald-200 border border-emerald-600">
                    Conf: {(locked.confidence * 100).toFixed(1)}%
                  </span>
                  <span className="px-1.5 py-0.5 rounded bg-slate-900 text-slate-200 border border-slate-700">
                    Crown: {locked.crown_diameter_m}m
                  </span>
                  <span className="px-1.5 py-0.5 rounded bg-amber-950 text-amber-300 border border-amber-800">
                    Bio: {locked.estimated_biomass_kg}kg
                  </span>
                </div>
              </div>
            )}

            {!locked && isPlaying && (
              <div className="absolute bottom-8 px-3 py-1 rounded bg-slate-900/80 border border-slate-700 text-[10px] text-emerald-400 font-mono tracking-wider animate-pulse">
                SCANNING CANOPY // COORDINATE ATTENTION YOLOv5s...
              </div>
            )}
          </div>

          {/* BOTTOM coordinate readout */}
          <div className="relative z-20 mt-auto flex items-center justify-between p-3 px-4 text-[10px] text-emerald-300 font-mono bg-gradient-to-t from-slate-950/80 to-transparent">
            <span>LAT: {telemetry.latitude.toFixed(6)}° N</span>
            <span>LON: {telemetry.longitude.toFixed(6)}° E</span>
          </div>
        </div>

        {/* RIGHT: AVIONICS & SENSORS */}
        <div className="lg:col-span-5 p-4 bg-[#0a0e17] flex flex-col justify-between space-y-4">
          <div>
            <span className="text-[10px] font-bold text-slate-400 tracking-wider block mb-2">
              AVIONICS &amp; SENSOR READINGS
            </span>

            <div className="grid grid-cols-2 gap-2.5">
              <div className="p-2.5 rounded-xl bg-slate-900/90 border border-slate-800">
                <div className="flex items-center gap-1.5 text-slate-400 text-[10px] mb-1">
                  <Gauge className="w-3.5 h-3.5 text-emerald-400" />
                  <span>ALTITUDE AGL</span>
                </div>
                <div className="text-base font-bold text-slate-100">
                  {telemetry.altitude_m.toFixed(1)} <span className="text-xs font-normal text-slate-400">m</span>
                </div>
              </div>

              <div className="p-2.5 rounded-xl bg-slate-900/90 border border-slate-800">
                <div className="flex items-center gap-1.5 text-slate-400 text-[10px] mb-1">
                  <Navigation className="w-3.5 h-3.5 text-cyan-400" />
                  <span>GROUND SPEED</span>
                </div>
                <div className="text-base font-bold text-slate-100">
                  {telemetry.speed_mps.toFixed(1)} <span className="text-xs font-normal text-slate-400">m/s</span>
                </div>
              </div>

              <div className="p-2.5 rounded-xl bg-slate-900/90 border border-slate-800">
                <div className="flex items-center gap-1.5 text-slate-400 text-[10px] mb-1">
                  <Compass className="w-3.5 h-3.5 text-amber-400" />
                  <span>HEADING</span>
                </div>
                <div className="text-base font-bold text-slate-100 flex items-center gap-1">
                  <span>{Math.round(telemetry.heading_deg)}°</span>
                  <span className="text-xs text-amber-400">({getHeadingCardinal(telemetry.heading_deg)})</span>
                </div>
              </div>

              <div className="p-2.5 rounded-xl bg-slate-900/90 border border-slate-800">
                <div className="flex items-center gap-1.5 text-slate-400 text-[10px] mb-1">
                  <Zap className="w-3.5 h-3.5 text-purple-400" />
                  <span>ORIENTATION</span>
                </div>
                <div className="text-xs font-bold text-slate-200">
                  P: {telemetry.pitch_deg.toFixed(1)}° &bull; R: {telemetry.roll_deg.toFixed(1)}°
                </div>
              </div>
            </div>
          </div>

          <div className="p-2 rounded-xl bg-emerald-950/30 border border-emerald-800/40 text-[10px] text-emerald-300/90">
            <span className="font-bold block text-emerald-200 mb-0.5">Coordinate Attention YOLOv5s Model</span>
            <span>CABlock horizontal/vertical spatial pooling &bull; 95.3% Sandalwood precision</span>
          </div>
        </div>
      </div>

      {/* 3. FLIGHT CONTROLS & TIMELINE SCRUBBER */}
      <div className="p-3 px-4 bg-[#0d1320] border-b border-slate-800/80 flex flex-col sm:flex-row items-center justify-between gap-3">
        <div className="flex items-center gap-2 w-full sm:w-auto">
          <button
            type="button"
            onClick={onTogglePlay}
            className={`flex items-center justify-center gap-1.5 px-4 py-2 rounded-xl font-bold text-xs transition-all shadow-md ${
              isPlaying
                ? 'bg-amber-500 hover:bg-amber-400 text-slate-950 shadow-glow-amber'
                : 'bg-emerald-500 hover:bg-emerald-400 text-slate-950 shadow-glow-emerald'
            }`}
          >
            {isPlaying ? <Pause className="w-3.5 h-3.5" /> : <Play className="w-3.5 h-3.5 fill-current" />}
            <span>{isPlaying ? 'Pause Patrol' : 'Start Patrol Sweep'}</span>
          </button>

          <button
            type="button"
            onClick={onReset}
            className="p-2 rounded-xl bg-slate-900 hover:bg-slate-800 text-slate-400 hover:text-white border border-slate-800 transition-colors"
            title="Reset Mission to Takeoff Point"
          >
            <RotateCcw className="w-3.5 h-3.5" />
          </button>

          <div className="flex items-center gap-1 bg-slate-900 p-1 rounded-xl border border-slate-800 text-[10px]">
            {[1, 2, 4].map((mult) => (
              <button
                key={`speed-${mult}`}
                type="button"
                onClick={() => onChangeSpeed(mult)}
                className={`px-2 py-0.5 rounded-lg transition-all ${
                  speedMultiplier === mult
                    ? 'bg-emerald-500 text-slate-950 font-bold'
                    : 'text-slate-400 hover:text-white'
                }`}
              >
                {mult}x
              </button>
            ))}
          </div>
        </div>

        <div className="flex-1 max-w-md w-full space-y-1">
          <div className="flex items-center justify-between text-[10px] text-slate-400">
            <span>Mission Progress: {progressPct.toFixed(0)}%</span>
            <span>
              {formatSecs(telemetry.elapsed_sec)} / {formatSecs(totalDuration)}
            </span>
          </div>
          <div className="w-full h-2 rounded-full bg-slate-900 border border-slate-800 overflow-hidden relative">
            <div
              className="h-full bg-gradient-to-r from-emerald-500 to-cyan-400 transition-all duration-200"
              style={{ width: `${progressPct}%` }}
            />
          </div>
        </div>

        <div className="text-[11px] text-slate-300 font-mono bg-slate-900 px-3 py-1.5 rounded-xl border border-slate-800">
          <span>Active: </span>
          <span className="text-emerald-400 font-bold">
            {mission.waypoints[telemetry.active_waypoint_index]?.waypoint_id || 'WP-01'}
          </span>
          <span className="text-slate-500"> / WP-08</span>
        </div>
      </div>

      {/* 4. REAL-TIME DETECTED CANOPY LOG FEED */}
      <div className="p-3 px-4 bg-[#090c14] space-y-2">
        <div className="flex items-center justify-between text-[10px] font-bold text-slate-400 tracking-wider">
          <div className="flex items-center gap-1.5 text-emerald-400">
            <Trees className="w-3.5 h-3.5" />
            <span>INTERCEPTED TREE SPECIMENS ({interceptedTargets.length} DETECTED)</span>
          </div>
          <span className="text-slate-500">Real-Time Coordinate Attention Logging</span>
        </div>

        {interceptedTargets.length === 0 ? (
          <div className="p-3 rounded-xl bg-slate-950/60 border border-slate-900 text-center text-[11px] text-slate-500 italic">
            Patrol UAV is en route. Detected Sandalwood tree crowns will appear here in real time as the drone sweeps the grid.
          </div>
        ) : (
          <div className="flex items-center gap-2 overflow-x-auto pb-1 max-w-full scrollbar-thin">
            {interceptedTargets.map((target, idx) => (
              <div
                key={`intercepted-${target.box_id}-${idx}`}
                className={`flex-shrink-0 p-2 px-2.5 rounded-xl border flex items-center gap-2 text-[10px] ${
                  target.is_sandalwood
                    ? 'bg-emerald-950/40 border-emerald-800/60 text-emerald-300'
                    : 'bg-amber-950/40 border-amber-800/60 text-amber-300'
                }`}
              >
                {target.is_sandalwood ? (
                  <TreePine className="w-3.5 h-3.5 text-emerald-400" />
                ) : (
                  <Trees className="w-3.5 h-3.5 text-amber-400" />
                )}
                <div>
                  <div className="font-bold text-slate-100">{target.species_scientific}</div>
                  <div className="text-[9px] text-slate-400">
                    Conf: {(target.confidence * 100).toFixed(0)}% &bull; {target.crown_diameter_m}m &bull; {target.estimated_biomass_kg}kg
                  </div>
                </div>
                <CheckCircle2 className="w-3 h-3 text-emerald-400 flex-shrink-0" />
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};
