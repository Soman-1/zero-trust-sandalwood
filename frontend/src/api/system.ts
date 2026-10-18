import apiClient from './client';
import { SystemInfoResponse } from '../types';

export const systemApi = {
  getSystemInfo: async (): Promise<SystemInfoResponse> => {
    const response = await apiClient.get<SystemInfoResponse>('/system/info');
    return response.data;
  },

  getHealth: async (): Promise<{ status: string; service: string; version: string; environment: string }> => {
    const response = await apiClient.get('/health', { baseURL: '' });
    return response.data;
  },
};
