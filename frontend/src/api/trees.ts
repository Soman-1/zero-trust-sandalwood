import apiClient from './client';
import { Tree, TreeStatus, NearbyTreesResponse } from '../types';

export const treesApi = {
  listTrees: async (params?: {
    region_id?: string;
    status?: TreeStatus;
    skip?: number;
    limit?: number;
  }): Promise<Tree[]> => {
    const response = await apiClient.get<Tree[]>('/trees', { params });
    return response.data;
  },

  getTree: async (treeUid: string): Promise<Tree> => {
    const response = await apiClient.get<Tree>(`/trees/${treeUid}`);
    return response.data;
  },

  registerTree: async (data: {
    tree_uid: string;
    species?: string;
    region_id?: number;
    latitude: number;
    longitude: number;
    estimated_age_years?: number;
    planting_year?: number | null;
    girth_cm?: number;
    height_m?: number;
    host_notes?: string;
    status?: TreeStatus;
    notes?: string;
    evidence_origin?: string;
  }): Promise<Tree> => {
    const response = await apiClient.post<Tree>('/trees', data);
    return response.data;
  },

  updateTree: async (
    treeUid: string,
    data: {
      estimated_age_years?: number;
      planting_year?: number | null;
      girth_cm?: number;
      height_m?: number;
      host_notes?: string;
      status?: TreeStatus;
      notes?: string;
    }
  ): Promise<Tree> => {
    const response = await apiClient.put<Tree>(`/trees/${treeUid}`, data);
    return response.data;
  },

  findNearby: async (params: {
    latitude: number;
    longitude: number;
    radius_meters?: number;
    limit?: number;
  }): Promise<NearbyTreesResponse> => {
    const response = await apiClient.post<NearbyTreesResponse>('/trees/nearby', params);
    return response.data;
  },
  deleteTree: async (treeUid: string): Promise<{ tree_uid: string; deleted: boolean }> => {
    const response = await apiClient.delete<{ tree_uid: string; deleted: boolean }>(
      `/trees/${encodeURIComponent(treeUid)}/record`
    );
    return response.data;
  },

  updateTreeStatus: async (treeUid: string, data: { status: TreeStatus; reason?: string }): Promise<Tree> => {
    const response = await apiClient.patch<Tree>(`/trees/${treeUid}/status`, data);
    return response.data;
  },
};
