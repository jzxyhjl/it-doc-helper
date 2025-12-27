/**
 * 文档相关API
 */
import apiClient from './client'
import type {
  DocumentUploadResponse,
  DocumentResponse,
  DocumentProgressResponse,
  DocumentResultResponse,
  MultiViewResultResponse,
  SimilarDocumentsResponse,
  RecommendationsResponse
} from '../types'

export const documentsApi = {
  /**
   * 上传文档
   */
  upload: async (file: File): Promise<DocumentUploadResponse> => {
    // #region agent log
    fetch('http://127.0.0.1:7242/ingest/eeaccba4-a712-43c7-b379-db4639c44cbf',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'documents.ts:18',message:'upload function entry',data:{fileName:file.name,fileSize:file.size,fileType:file.type},timestamp:Date.now(),sessionId:'debug-session',runId:'run1',hypothesisId:'E'})}).catch(()=>{});
    // #endregion
    const formData = new FormData()
    formData.append('file', file)
    
    // #region agent log
    fetch('http://127.0.0.1:7242/ingest/eeaccba4-a712-43c7-b379-db4639c44cbf',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'documents.ts:23',message:'Before axios post',data:{baseURL:apiClient.defaults.baseURL,url:'/documents/upload'},timestamp:Date.now(),sessionId:'debug-session',runId:'run1',hypothesisId:'F'})}).catch(()=>{});
    // #endregion
    // 使用axios的默认行为，它会自动设置正确的Content-Type（包括boundary）
    const response = await apiClient.post('/documents/upload', formData)
    // #region agent log
    fetch('http://127.0.0.1:7242/ingest/eeaccba4-a712-43c7-b379-db4639c44cbf',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'documents.ts:26',message:'axios post succeeded',data:{status:response.status,statusText:response.statusText},timestamp:Date.now(),sessionId:'debug-session',runId:'run1',hypothesisId:'G'})}).catch(()=>{});
    // #endregion
    
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
   * 注意：当不指定view和views时，返回MultiViewResultResponse；指定时返回DocumentResultResponse或ViewsResultResponse
   */
  getResult: async (
    documentId: string,
    view?: string,
    views?: string
  ): Promise<DocumentResultResponse | MultiViewResultResponse> => {
    const params = new URLSearchParams()
    if (view) params.append('view', view)
    if (views) params.append('views', views)
    
    const queryString = params.toString()
    const url = `/documents/${documentId}/result${queryString ? `?${queryString}` : ''}`
    const response = await apiClient.get(url)
    return response.data
  },

  /**
   * 推荐视角
   */
  recommendViews: async (documentId: string): Promise<{
    primary_view: string
    enabled_views: string[]
    detection_scores: Record<string, number>
    cache_key?: string
  }> => {
    const response = await apiClient.post(`/documents/${documentId}/recommend-views`)
    return response.data
  },

  /**
   * 获取视角状态
   */
  getViewsStatus: async (documentId: string): Promise<{
    document_id: string
    views_status: Record<string, {
      view: string
      status: 'completed' | 'processing' | 'pending' | 'failed'
      ready: boolean
      is_primary: boolean
      processing_time?: number
    }>
    primary_view?: string
    enabled_views: string[]
  }> => {
    const response = await apiClient.get(`/documents/${documentId}/views/status`)
    return response.data
  },

  /**
   * 切换视角
   */
  switchView: async (documentId: string, view: string): Promise<DocumentResultResponse> => {
    const response = await apiClient.post(`/documents/${documentId}/switch-view?view=${view}`)
    return response.data
  },

  /**
   * 删除文档
   */
  delete: async (documentId: string): Promise<void> => {
    await apiClient.delete(`/documents/${documentId}`)
  },

  /**
   * 批量删除文档
   */
  batchDelete: async (documentIds: string[]): Promise<{ success_count: number; failed_count: number; failed_ids: string[] }> => {
    const response = await apiClient.post('/documents/batch-delete', documentIds)
    return response.data
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

