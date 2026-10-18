import apiClient from './client';
import { Region, RegionStatus, CoordinateCheckResponse, GeoJSONPolygon } from '../types';

export const regionsApi = {
  listRegions: async (params?: {
    status?: RegionStatus;
    skip?: number;
    limit?: number;
  }): Promise<Region[]> => {
    const response = await apiClient.get<Region[]>('/regions', { params });
    return response.data;
  },

  getRegion: async (regionId: string): Promise<Region> => {
    const response = await apiClient.get<Region>(`/regions/${regionId}`);
    return response.data;
  },

  createRegion: async (data: {
    region_id: string;
    name: string;
    description?: string;
    boundary_geojson: GeoJSONPolygon;
    center_latitude: number;
    center_longitude: number;
    area_hectares: number;
    status?: RegionStatus;
  }): Promise<Region> => {
    const response = await apiClient.post<Region>('/regions', data);
    return response.data;
  },

  updateRegion: async (
    regionId: string,
    data: {
      name?: string;
      description?: string;
      boundary_geojson?: GeoJSONPolygon;
      center_latitude?: number;
      center_longitude?: number;
      area_hectares?: number;
      status?: RegionStatus;
    }
  ): Promise<Region> => {
    const response = await apiClient.put<Region>(`/regions/${regionId}`, data);
    return response.data;
  },

  checkCoordinate: async (
    regionId: string,
    coordinates: { latitude: number; longitude: number }
  ): Promise<CoordinateCheckResponse> => {
    const response = await apiClient.post<CoordinateCheckResponse>(
      `/regions/${regionId}/check-coordinate`,
      coordinates
    );
    return response.data;
  },

  decommissionRegion: async (regionId: string): Promise<Region> => {
    const response = await apiClient.delete<Region>(`/regions/${regionId}`);
    return response.data;
  },
};
