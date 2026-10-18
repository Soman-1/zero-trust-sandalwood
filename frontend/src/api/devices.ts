import apiClient from './client';
import { Device, DeviceStatus, DeviceRegisterResponse, DeviceType } from '../types';

export const devicesApi = {
  listDevices: async (params?: {
    status?: DeviceStatus;
    region_id?: number;
    skip?: number;
    limit?: number;
  }): Promise<Device[]> => {
    const response = await apiClient.get<Device[]>('/devices', { params });
    return response.data;
  },

  getDevice: async (deviceId: string): Promise<Device> => {
    const response = await apiClient.get<Device>(`/devices/${deviceId}`);
    return response.data;
  },

  registerDevice: async (data: {
    device_id: string;
    name: string;
    device_type: DeviceType;
    assigned_region_id?: number;
    initial_latitude?: number;
    initial_longitude?: number;
  }): Promise<DeviceRegisterResponse> => {
    const response = await apiClient.post<DeviceRegisterResponse>('/devices', data);
    return response.data;
  },

  updateDeviceStatus: async (deviceId: string, status: DeviceStatus): Promise<Device> => {
    const response = await apiClient.patch<Device>(`/devices/${deviceId}/status`, { status });
    return response.data;
  },

  // Simulating device telemetry heartbeat
  sendHeartbeat: async (deviceId: string, apiKey: string, latitude: number, longitude: number) => {
    const response = await apiClient.post('/devices/heartbeat', { latitude, longitude }, {
      headers: {
        'X-Device-ID': deviceId,
        'X-Device-Key': apiKey,
      }
    });
    return response.data;
  },
};
