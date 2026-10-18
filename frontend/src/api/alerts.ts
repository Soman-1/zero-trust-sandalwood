import apiClient from './client';
import {
  Alert,
  AlertSeverity,
  AlertStatus,
  AlertSummaryStatsResponse,
  PaginatedAlertsResponse,
} from '../types';

export const alertsApi = {
  listAlerts: async (params?: {
    status?: AlertStatus;
    severity?: AlertSeverity;
    region_id?: string;
    tree_id?: string;
    skip?: number;
    limit?: number;
  }): Promise<PaginatedAlertsResponse> => {
    const response = await apiClient.get<PaginatedAlertsResponse>('/alerts', { params });
    return response.data;
  },

  getSummaryStats: async (regionId?: string): Promise<AlertSummaryStatsResponse> => {
    const response = await apiClient.get<AlertSummaryStatsResponse>('/alerts/summary/stats', {
      params: regionId ? { region_id: regionId } : undefined,
    });
    return response.data;
  },

  getAlert: async (alertUid: string): Promise<Alert> => {
    const response = await apiClient.get<Alert>(`/alerts/${alertUid}`);
    return response.data;
  },

  createAlert: async (data: {
    tree_id?: number;
    device_id?: number;
    severity: AlertSeverity;
    title: string;
    description: string;
  }): Promise<Alert> => {
    const response = await apiClient.post<Alert>('/alerts', data);
    return response.data;
  },

  acknowledgeAlert: async (alertUid: string): Promise<Alert> => {
    const response = await apiClient.post<Alert>(`/alerts/${alertUid}/acknowledge`);
    return response.data;
  },

  resolveAlert: async (alertUid: string, notes?: string): Promise<Alert> => {
    const response = await apiClient.post<Alert>(`/alerts/${alertUid}/resolve`, {
      resolution_notes: notes || 'Resolved by operator',
    });
    return response.data;
  },

  dismissAlert: async (alertUid: string, notes?: string): Promise<Alert> => {
    const response = await apiClient.post<Alert>(`/alerts/${alertUid}/dismiss`, {
      dismissal_reason: notes || 'Dismissed as false alarm',
    });
    return response.data;
  },
};
