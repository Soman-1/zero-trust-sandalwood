import apiClient from './client';
import {
  EnvironmentalMeasurement,
  PaginatedMeasurementsResponse,
  MeasurementStatsResponse,
  IntegrityCheckResponse,
  IntegrityScanResponse,
} from '../types';

export const measurementsApi = {
  listMeasurements: async (params?: {
    region_id?: string;
    tree_id?: string;
    start_time?: string;
    end_time?: string;
    is_anomaly?: boolean;
    skip?: number;
    limit?: number;
  }): Promise<PaginatedMeasurementsResponse> => {
    const response = await apiClient.get<PaginatedMeasurementsResponse>('/measurements', { params });
    return response.data;
  },

  getMeasurement: async (measurementUid: string): Promise<EnvironmentalMeasurement> => {
    const response = await apiClient.get<EnvironmentalMeasurement>(`/measurements/${measurementUid}`);
    return response.data;
  },

  getStats: async (params?: {
    region_id?: string;
    tree_id?: string;
    start_time?: string;
    end_time?: string;
  }): Promise<MeasurementStatsResponse> => {
    const response = await apiClient.get<MeasurementStatsResponse>('/measurements/analytics/stats', {
      params,
    });
    return response.data;
  },

  getLatestForRegion: async (regionId: string): Promise<EnvironmentalMeasurement> => {
    const response = await apiClient.get<EnvironmentalMeasurement>(
      `/measurements/region/${regionId}/latest`
    );
    return response.data;
  },

  getLatestForTree: async (treeUid: string): Promise<EnvironmentalMeasurement> => {
    const response = await apiClient.get<EnvironmentalMeasurement>(
      `/measurements/tree/${treeUid}/latest`
    );
    return response.data;
  },

  getTreeHistory: async (
    treeUid: string,
    params?: { skip?: number; limit?: number }
  ): Promise<EnvironmentalMeasurement[]> => {
    const response = await apiClient.get<EnvironmentalMeasurement[]>(
      `/measurements/tree/${treeUid}/history`,
      { params }
    );
    return response.data;
  },

  // Zero Trust Cryptographic Integrity Checks
  verifyMeasurementIntegrity: async (measurementUid: string): Promise<IntegrityCheckResponse> => {
    const response = await apiClient.post<IntegrityCheckResponse>(
      `/measurements/${measurementUid}/verify-integrity`
    );
    return response.data;
  },

  scanIntegrityAudit: async (params?: {
    region_id?: string;
    limit?: number;
  }): Promise<IntegrityScanResponse> => {
    const response = await apiClient.post<IntegrityScanResponse>(
      '/measurements/integrity/audit-scan',
      null,
      { params }
    );
    return response.data;
  },

  // Field IoT Ingestion simulation
  ingestSingle: async (
    deviceId: string,
    apiKey: string,
    payload: {
      tree_id?: string;
      latitude: number;
      longitude: number;
      temperature: number;
      humidity: number;
      soil_moisture: number;
      recorded_at?: string;
    }
  ) => {
    const response = await apiClient.post('/measurements/ingest', payload, {
      headers: {
        'X-Device-ID': deviceId,
        'X-Device-Key': apiKey,
      },
    });
    return response.data;
  },
};
