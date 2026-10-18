import apiClient from './client';
import {
  DashboardOverviewResponse,
  GISMapLayerResponse,
  TimeSeriesResponse,
  RegionDashboardResponse,
} from '../types';

export const dashboardApi = {
  getOverview: async (): Promise<DashboardOverviewResponse> => {
    const response = await apiClient.get<DashboardOverviewResponse>('/dashboard/overview');
    return response.data;
  },

  getMapLayer: async (regionId?: string): Promise<GISMapLayerResponse> => {
    const response = await apiClient.get<GISMapLayerResponse>('/dashboard/map-layer', {
      params: regionId ? { region_id: regionId } : undefined,
    });
    return response.data;
  },

  getTimeSeries: async (params?: {
    region_id?: string;
    tree_id?: string;
    hours?: number;
  }): Promise<TimeSeriesResponse> => {
    const response = await apiClient.get<TimeSeriesResponse>('/dashboard/timeseries', { params });
    return response.data;
  },

  getRegionDashboard: async (regionId: string): Promise<RegionDashboardResponse> => {
    const response = await apiClient.get<RegionDashboardResponse>(`/dashboard/region/${regionId}`);
    return response.data;
  },
};
