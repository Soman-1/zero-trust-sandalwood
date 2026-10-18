import apiClient from './client';
import { TokenResponse, User, PaginatedUsersResponse, UserRole, UserStatus } from '../types';

export const authApi = {
  login: async (credentials: { username_or_email: string; password: string }): Promise<TokenResponse> => {
    const response = await apiClient.post<TokenResponse>('/auth/login', credentials);
    return response.data;
  },

  register: async (userData: {
    username: string;
    email: string;
    password: string;
    full_name: string;
    role?: UserRole;
  }): Promise<User> => {
    const response = await apiClient.post<User>('/auth/register', userData);
    return response.data;
  },

  getMe: async (): Promise<User> => {
    const response = await apiClient.get<User>('/auth/me');
    return response.data;
  },

  logout: async (): Promise<{ success: boolean; message: string }> => {
    const response = await apiClient.post<{ success: boolean; message: string }>('/auth/logout');
    return response.data;
  },

  // Admin user management
  listUsers: async (params?: {
    role?: UserRole;
    status?: UserStatus;
    skip?: number;
    limit?: number;
  }): Promise<PaginatedUsersResponse> => {
    const response = await apiClient.get<PaginatedUsersResponse>('/auth/users', { params });
    return response.data;
  },

  updateUserStatus: async (userId: number, status: UserStatus): Promise<User> => {
    const response = await apiClient.put<User>(`/auth/users/${userId}/status`, { status });
    return response.data;
  },

  updateUserRole: async (userId: number, role: UserRole): Promise<User> => {
    const response = await apiClient.put<User>(`/auth/users/${userId}/role`, { role });
    return response.data;
  },
};
