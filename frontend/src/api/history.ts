/**
 * 历史记录API
 */
import apiClient from './client'
import type { DocumentHistoryResponse } from '../types'

export interface HistoryQueryParams {
  page?: number
  page_size?: number
  document_type?: string
  start_date?: string
  end_date?: string
}

export const historyApi = {
  /**
   * 获取历史记录列表
   */
  getHistory: async (params: HistoryQueryParams = {}): Promise<DocumentHistoryResponse> => {
    const response = await apiClient.get('/documents/history', { params })
    return response.data
  }
}

