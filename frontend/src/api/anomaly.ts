import apiClient from './client';
import {
  AnomalyEvaluateRequest,
  AnomalyEvaluateResponse,
  ModelStatusResponse,
  ModelRetrainResponse,
} from '../types';

export const anomalyApi = {
  evaluate: async (payload: AnomalyEvaluateRequest): Promise<AnomalyEvaluateResponse> => {
    const response = await apiClient.post<AnomalyEvaluateResponse>('/anomaly/evaluate', payload);
    return response.data;
  },

  getStatus: async (): Promise<ModelStatusResponse> => {
    const response = await apiClient.get<ModelStatusResponse>('/anomaly/model-status');
    return response.data;
  },

  retrainModel: async (minSamples: number = 10): Promise<ModelRetrainResponse> => {
    const response = await apiClient.post<ModelRetrainResponse>('/anomaly/train', null, {
      params: { min_samples: minSamples },
    });
    return response.data;
  },
};
