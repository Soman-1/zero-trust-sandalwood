import apiClient from './client';
import { Tree } from '../types';

export interface MapDetection {
  id: number;
  detection_uid: string;
  latitude: number;
  longitude: number;
  altitude?: number | null;
  species: string;
  source: string;
  confidence?: number | null;
  region_id?: number | null;
  status: 'UNASSIGNED' | 'ASSIGNED';
  notes?: string | null;
}

export const detectionsApi = {
  listUnassigned: async (): Promise<MapDetection[]> => {
    const response = await apiClient.get<MapDetection[]>('/detections');
    return response.data;
  },

  assignTreeId: async (
    detectionUid: string,
    data: {
      tree_uid: string;
      region_id?: number | string;
      species?: string;
      notes?: string;
    }
  ): Promise<Tree> => {
    const response = await apiClient.post<Tree>(`/detections/${detectionUid}/assign`, data);
    return response.data;
  },
};
