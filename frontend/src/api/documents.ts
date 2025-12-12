/**
 * 文档相关API
 */
import apiClient from './client'
import type {
  DocumentUploadResponse,
  DocumentResponse,
  DocumentProgressResponse,
  DocumentResultResponse,
  SimilarDocumentsResponse,
  RecommendationsResponse
} from '../types'

export const documentsApi = {
  /**
   * 上传文档
   */
  upload: async (file: File): Promise<DocumentUploadResponse> => {
    const formData = new FormData()
    formData.append('file', file)
    
    // 使用axios的默认行为，它会自动设置正确的Content-Type（包括boundary）
    const response = await apiClient.post('/documents/upload', formData)
    
    return response.data
  },

  /**
   * 获取文档信息
   */
  getDocument: async (documentId: string): Promise<DocumentResponse> => {
    const response = await apiClient.get(`/documents/${documentId}`)
    return response.data
  },

  /**
   * 获取处理进度
   */
  getProgress: async (documentId: string): Promise<DocumentProgressResponse> => {
    const response = await apiClient.get(`/documents/${documentId}/progress`)
    return response.data
  },

  /**
   * 获取处理结果
   */
  getResult: async (documentId: string): Promise<DocumentResultResponse> => {
    const response = await apiClient.get(`/documents/${documentId}/result`)
    return response.data
  },

  /**
   * 删除文档
   */
  delete: async (documentId: string): Promise<void> => {
    await apiClient.delete(`/documents/${documentId}`)
  },

  /**
   * 获取相似文档（已废弃，功能已合并到智能推荐）
   * @deprecated 使用 getRecommendations 代替
   */
  getSimilarDocuments: async (
    documentId: string,
    limit?: number,
    threshold?: number
  ): Promise<SimilarDocumentsResponse> => {
    const params = new URLSearchParams()
    if (limit !== undefined) params.append('limit', limit.toString())
    if (threshold !== undefined) params.append('threshold', threshold.toString())
    
    const queryString = params.toString()
    const url = `/documents/${documentId}/similar${queryString ? `?${queryString}` : ''}`
    const response = await apiClient.get(url)
    return response.data
  }
}

/**
 * 学习相关API
 */
export const learningApi = {
  /**
   * 获取智能推荐
   */
  getRecommendations: async (
    documentId?: string,
    limit?: number,
    documentType?: string,
    minQualityScore?: number
  ): Promise<RecommendationsResponse> => {
    const params = new URLSearchParams()
    if (documentId) params.append('document_id', documentId)
    if (limit !== undefined) params.append('limit', limit.toString())
    if (documentType) params.append('document_type', documentType)
    if (minQualityScore !== undefined) params.append('min_quality_score', minQualityScore.toString())
    
    const queryString = params.toString()
    const url = `/learning/recommendations${queryString ? `?${queryString}` : ''}`
    const response = await apiClient.get(url)
    return response.data
  }
}

