import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import Card from './ui/Card'
import LoadingSpinner from './ui/LoadingSpinner'
import { learningApi } from '../api/documents'
import type { RecommendationsResponse, RecommendedDocumentItem } from '../types'

interface RecommendationsProps {
  documentId?: string
  limit?: number
  documentType?: string
  minQualityScore?: number
  title?: string
}

export default function Recommendations({
  documentId,
  limit = 10,
  documentType,
  minQualityScore,
  title = "相关推荐"
}: RecommendationsProps) {
  const navigate = useNavigate()
  const [recommendations, setRecommendations] = useState<RecommendationsResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const fetchRecommendations = async () => {
      setLoading(true)
      setError(null)
      try {
        const data = await learningApi.getRecommendations(
          documentId,
          limit,
          documentType,
          minQualityScore
        )
        setRecommendations(data)
      } catch (err: any) {
        console.error('获取推荐失败:', err)
        console.error('错误详情:', {
          message: err.message,
          response: err.response?.data,
          status: err.response?.status,
          request: err.request
        })
        
        // 更详细的错误信息
        let errorMessage = '获取推荐失败'
        if (err.response?.data?.detail) {
          errorMessage = err.response.data.detail
        } else if (err.message) {
          errorMessage = err.message
        } else if (err.code === 'ECONNABORTED') {
          errorMessage = '请求超时，请稍后重试'
        } else if (!err.response && err.request) {
          errorMessage = '网络连接失败，请检查网络'
        }
        
        setError(errorMessage)
      } finally {
        setLoading(false)
      }
    }

    if (documentId) {
      fetchRecommendations()
    }
  }, [documentId, limit, documentType, minQualityScore])

  if (loading) {
    return (
      <Card title={title}>
        <div className="text-center py-4">
          <LoadingSpinner size="sm" />
          <p className="mt-2 text-sm text-gray-500">加载推荐中...</p>
        </div>
      </Card>
    )
  }

  if (error) {
    return (
      <Card title={title}>
        <div className="text-center py-4 text-red-500 text-sm">
          {error}
        </div>
      </Card>
    )
  }

  if (!recommendations || recommendations.recommendations.length === 0) {
    return (
      <Card title={title}>
        <div className="text-center py-4 text-gray-500 text-sm">
          暂无推荐文档
        </div>
      </Card>
    )
  }

  const getDocumentTypeLabel = (type: string) => {
    const labels: Record<string, string> = {
      interview: '面试题',
      technical: '技术文档',
      architecture: '架构文档',
      unknown: '未知'
    }
    return labels[type] || type
  }

  const getDocumentTypeColor = (type: string) => {
    const colors: Record<string, string> = {
      interview: 'bg-blue-100 text-blue-800',
      technical: 'bg-green-100 text-green-800',
      architecture: 'bg-purple-100 text-purple-800',
      unknown: 'bg-gray-100 text-gray-800'
    }
    return colors[type] || 'bg-gray-100 text-gray-800'
  }

  const getRecommendationScoreColor = (score: number) => {
    if (score >= 0.8) return 'text-green-600'
    if (score >= 0.6) return 'text-yellow-600'
    return 'text-orange-600'
  }

  return (
    <Card title={title}>
      <div className="space-y-3">
        {recommendations.recommendations.map((doc: RecommendedDocumentItem, index: number) => (
          <div
            key={doc.document_id || `book-${index}`}
            className={`border border-gray-200 rounded-lg p-4 hover:border-primary-300 hover:shadow-md transition-all ${
              doc.is_book ? 'cursor-default' : 'cursor-pointer'
            }`}
            onClick={() => {
              if (!doc.is_book && doc.document_id) {
                navigate(`/result/${doc.document_id}`)
              }
            }}
          >
            <div className="flex items-start justify-between mb-2">
              <div className="flex-1">
                <div className="flex items-center gap-2 mb-1">
                  <h4 className="font-medium text-gray-900">{doc.filename}</h4>
                  {doc.is_book && (
                    <span className="px-2 py-0.5 bg-orange-100 text-orange-800 rounded text-xs font-medium">
                      书籍推荐
                    </span>
                  )}
                </div>
                {doc.author && (
                  <p className="text-xs text-gray-500 mb-2">作者: {doc.author}</p>
                )}
                <div className="flex items-center gap-2 mb-2 flex-wrap">
                  <span className={`px-2 py-1 rounded text-xs font-medium ${getDocumentTypeColor(doc.document_type)}`}>
                    {getDocumentTypeLabel(doc.document_type)}
                  </span>
                  {doc.quality_score !== undefined && doc.quality_score !== null && (
                    <span className={`text-xs font-medium ${
                      doc.quality_score >= 80 ? 'text-green-600' :
                      doc.quality_score >= 60 ? 'text-yellow-600' : 'text-red-600'
                    }`}>
                      质量: {doc.quality_score}
                    </span>
                  )}
                  {doc.upload_time && (
                    <span className="text-xs text-gray-500">
                      {new Date(doc.upload_time).toLocaleDateString('zh-CN')}
                    </span>
                  )}
                </div>
              </div>
              <div className="text-right ml-4">
                <div className={`text-sm font-semibold ${getRecommendationScoreColor(doc.recommendation_score)} mb-1`}>
                  {(doc.recommendation_score * 100).toFixed(0)}%
                </div>
                <div className="text-xs text-gray-500">推荐度</div>
              </div>
            </div>
            
            {doc.content_summary && (
              <p className="text-sm text-gray-600 line-clamp-2 mt-2 mb-2">
                {doc.content_summary}
              </p>
            )}
            
            {doc.reasons && doc.reasons.length > 0 && (
              <div className="flex items-center gap-2 flex-wrap mt-2">
                <span className="text-xs text-gray-500">推荐理由：</span>
                {doc.reasons.map((reason, index) => (
                  <span
                    key={index}
                    className="px-2 py-1 bg-primary-50 text-primary-700 rounded text-xs"
                  >
                    {reason}
                  </span>
                ))}
              </div>
            )}
          </div>
        ))}
      </div>
      {recommendations.total > recommendations.recommendations.length && (
        <div className="mt-4 text-sm text-gray-500 text-center">
          显示 {recommendations.recommendations.length} / {recommendations.total} 个推荐
        </div>
      )}
    </Card>
  )
}

