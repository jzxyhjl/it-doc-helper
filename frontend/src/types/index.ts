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
  enabled_views?: string[]  // 启用的视角列表
  primary_view?: string     // 主视角
  task_id?: string          // 处理任务ID（用于WebSocket连接）
}

export interface DocumentResultResponse {
  document_id: string
  document_type: string
  result: any
  processing_time?: number
  quality_score?: number
  created_at: string
}

// 多视角结果响应
export interface MultiViewResultResponse {
  document_id: string
  views: Record<string, any>  // 后端返回的是字典，key是view名称，value是结果
  meta?: {
    enabled_views: string[]
    primary_view?: string
    confidence?: Record<string, number>
    view_count?: number
    timestamp?: string
  }
}

// 视角状态响应
export interface ViewsStatusResponse {
  document_id: string
  views_status: Record<string, {
    view: string
    status: 'completed' | 'processing' | 'pending' | 'failed'
    ready: boolean
    is_primary: boolean
    processing_time?: number
    has_content?: boolean  // 是否有内容（用于判断是否显示切换按钮），可选字段以兼容旧版本API
  }>
  primary_view?: string
  enabled_views: string[]
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

