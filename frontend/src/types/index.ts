/**
 * 类型定义
 */

export interface DocumentUploadResponse {
  document_id: string
  task_id?: string
  filename: string
  file_size: number
  file_type: string
  status: string
  upload_time: string
}

export interface DocumentResponse {
  document_id: string
  filename: string
  file_size: number
  file_type: string
  status: string
  upload_time: string
  created_at: string
  updated_at: string
}

export interface DocumentProgressResponse {
  document_id: string
  progress: number
  current_stage?: string
  status: string
}

export interface DocumentResultResponse {
  document_id: string
  document_type: string
  result: any
  processing_time?: number
  quality_score?: number
  created_at: string
}

export interface DocumentHistoryItem {
  document_id: string
  filename: string
  file_type: string
  document_type?: string
  status: string
  upload_time: string
  processing_time?: number
}

export interface DocumentHistoryResponse {
  total: number
  page: number
  page_size: number
  items: DocumentHistoryItem[]
}

/**
 * @deprecated 相似文档功能已合并到智能推荐，请使用 RecommendedDocumentItem
 */
export interface SimilarDocumentItem {
  document_id: string
  filename: string
  file_type: string
  document_type: string
  similarity: number
  content_summary?: string
  upload_time: string
}

/**
 * @deprecated 相似文档功能已合并到智能推荐，请使用 RecommendationsResponse
 */
export interface SimilarDocumentsResponse {
  document_id: string
  total: number
  limit: number
  threshold?: number
  items: SimilarDocumentItem[]
}

export interface RecommendedDocumentItem {
  is_book?: boolean
  author?: string
  document_id: string
  filename: string
  file_type: string
  document_type: string
  content_summary?: string
  quality_score?: number
  upload_time?: string
  similarity?: number
  recommendation_score: number
  reasons: string[]
}

export interface RecommendationsResponse {
  recommendations: RecommendedDocumentItem[]
  total: number
  generated_at: string
  error?: string
}

