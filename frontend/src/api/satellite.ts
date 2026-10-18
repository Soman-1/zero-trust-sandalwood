import apiClient from './client';
import {
  LiveClimateResponse,
  AerialPresetsResponse,
  AerialDetectResponse,
  DronePatrolMissionResponse,
} from '../types';

export interface AerialDetectPayload {
  preset_id?: string;
  image_base64?: string;
  confidence_threshold?: number;
  center_lat?: number;
  center_lon?: number;
  ground_sampling_distance_cm?: number;
}

export const satelliteApi = {
  getLiveWeather: async (latitude: number, longitude: number): Promise<LiveClimateResponse> => {
    const response = await apiClient.get<LiveClimateResponse>('/satellite/live-weather', {
      params: { latitude, longitude },
    });
    return response.data;
  },

  getAerialPresets: async (): Promise<AerialPresetsResponse> => {
    const response = await apiClient.get<AerialPresetsResponse>('/satellite/aerial-presets');
    return response.data;
  },

  detectAerialCanopies: async (payload: AerialDetectPayload): Promise<AerialDetectResponse> => {
    const response = await apiClient.post<AerialDetectResponse>('/satellite/detect-aerial', payload);
    return response.data;
  },

  getDronePatrolMission: async (
    presetId: string = 'shivamogga_plantation',
    speedMps: number = 8.0
  ): Promise<DronePatrolMissionResponse> => {
    const response = await apiClient.get<DronePatrolMissionResponse>('/satellite/drone-patrol-mission', {
      params: { preset_id: presetId, speed_mps: speedMps },
    });
    return response.data;
  },
};
