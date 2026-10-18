import apiClient from './client';
import {
  GlobalTreeItem,
  GlobalTreeStatsResponse,
  GlobalTreeImportResponse,
  GlobalTreeEnvironmentSnapshot,
  GlobalTreeRegisterResponse,
} from '../types';

export const globalTreesApi = {
  listTrees: async (params?: {
    source?: string;
    state?: string;
    has_photo?: boolean;
    query?: string;
    limit?: number;
  }): Promise<GlobalTreeItem[]> => {
    const response = await apiClient.get<GlobalTreeItem[]>('/global-trees', { params });
    return response.data;
  },

  getStats: async (): Promise<GlobalTreeStatsResponse> => {
    const response = await apiClient.get<GlobalTreeStatsResponse>('/global-trees/stats');
    return response.data;
  },

  importAll: async (): Promise<GlobalTreeImportResponse> => {
    const response = await apiClient.post<GlobalTreeImportResponse>('/global-trees/import-all');
    return response.data;
  },

  getEnvironment: async (occurrenceId: string): Promise<GlobalTreeEnvironmentSnapshot> => {
    const response = await apiClient.get<GlobalTreeEnvironmentSnapshot>('/global-trees/environment', {
      params: { occurrence_id: occurrenceId },
    });
    return response.data;
  },

  registerSelected: async (data: {
    occurrence_id: string;
    tree_uid: string;
    notes?: string;
  }): Promise<GlobalTreeRegisterResponse> => {
    const response = await apiClient.post<GlobalTreeRegisterResponse>('/global-trees/register', data);
    return response.data;
  },
};
