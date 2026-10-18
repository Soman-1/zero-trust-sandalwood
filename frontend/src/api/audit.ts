import apiClient from './client';
import {
  PaginatedAuditLogsResponse,
  AuditChainVerifyResponse,
  BlockchainAnchorResponse,
} from '../types';

export const auditApi = {
  listLogs: async (params?: {
    event_type?: string;
    actor_id?: string;
    start_time?: string;
    end_time?: string;
    skip?: number;
    limit?: number;
  }): Promise<PaginatedAuditLogsResponse> => {
    const response = await apiClient.get<PaginatedAuditLogsResponse>('/audit/logs', { params });
    return response.data;
  },

  verifyChain: async (): Promise<AuditChainVerifyResponse> => {
    const response = await apiClient.get<AuditChainVerifyResponse>('/audit/verify-chain');
    return response.data;
  },

  anchorToBlockchain: async (batchSize: number = 50): Promise<BlockchainAnchorResponse> => {
    // Chain receipt wait can take up to 120s; keep client timeout above that.
    const response = await apiClient.post<BlockchainAnchorResponse>(
      '/audit/blockchain-anchor',
      { batch_size: batchSize },
      { timeout: 130000 },
    );
    return response.data;
  },

  verifyOnChain: async (merkleRoot: string): Promise<{
    is_anchored: boolean;
    tx_hash?: string | null;
    block_number?: number | null;
    timestamp?: number | null;
    batch_size?: number | null;
    recorder?: string | null;
    contract_address?: string;
    source?: string;
    message?: string;
  }> => {
    const response = await apiClient.get('/audit/blockchain-verify', {
      params: { merkle_root: merkleRoot },
    });
    return response.data;
  },
};
