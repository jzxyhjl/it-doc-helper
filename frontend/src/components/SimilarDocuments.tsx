/**
 * 相似文档组件（已废弃）
 * @deprecated 功能已合并到 Recommendations 组件，请使用 Recommendations 代替
 */
import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import Card from './ui/Card'
import LoadingSpinner from './ui/LoadingSpinner'
import { documentsApi } from '../api/documents'
import type { SimilarDocumentsResponse, SimilarDocumentItem } from '../types'

interface SimilarDocumentsProps {
  documentId: string
}

/**
 * @deprecated 请使用 Recommendations 组件代替
 */
export default function SimilarDocuments({ documentId }: SimilarDocumentsProps) {
  const navigate = useNavigate()
  const [similarDocs, setSimilarDocs] = useState<SimilarDocumentsResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const fetchSimilarDocuments = async () => {
      try {
        const data = await documentsApi.getSimilarDocuments(documentId, 5)
        setSimilarDocs(data)
      } catch (err: any) {
        // 如果文档没有向量或不存在，不显示错误，只隐藏组件
        if (err.response?.status === 404) {
          setError(null)
        } else {
          setError(err.response?.data?.detail || '获取相似文档失败')
        }
      } finally {
        setLoading(false)
      }
    }

    if (documentId) {
      fetchSimilarDocuments()
    }
  }, [documentId])

  if (loading) {
    return (
      <Card title="相似文档">
        <div className="text-center py-4">
          <LoadingSpinner size="sm" />
          <p className="mt-2 text-sm text-gray-500">加载相似文档...</p>
        </div>
      </Card>
    )
  }

  if (error) {
    return null // 静默失败，不显示错误
  }

  if (!similarDocs || similarDocs.items.length === 0) {
    return (
      <Card title="相似文档">
        <div className="text-center py-4 text-gray-500 text-sm">
          暂无相似文档
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

  const formatSimilarity = (similarity: number) => {
    return `${(similarity * 100).toFixed(1)}%`
  }

  const getSimilarityColor = (similarity: number) => {
    if (similarity >= 0.7) return 'bg-green-500'
    if (similarity >= 0.5) return 'bg-yellow-500'
    return 'bg-orange-500'
  }

  return (
    <Card title="相似文档">
      <div className="space-y-3">
        {similarDocs.items.map((doc: SimilarDocumentItem) => (
          <div
            key={doc.document_id}
            className="border border-gray-200 rounded-lg p-4 hover:border-primary-300 hover:shadow-md transition-all cursor-pointer"
            onClick={() => navigate(`/result/${doc.document_id}`)}
          >
            <div className="flex items-start justify-between mb-2">
              <div className="flex-1">
                <h4 className="font-medium text-gray-900 mb-1">{doc.filename}</h4>
                <div className="flex items-center gap-2 mb-2">
                  <span className={`px-2 py-1 rounded text-xs font-medium ${getDocumentTypeColor(doc.document_type)}`}>
                    {getDocumentTypeLabel(doc.document_type)}
                  </span>
                  <span className="text-xs text-gray-500">
                    {new Date(doc.upload_time).toLocaleDateString('zh-CN')}
                  </span>
                </div>
              </div>
              <div className="text-right ml-4">
                <div className="text-sm font-semibold text-gray-900 mb-1">
                  {formatSimilarity(doc.similarity)}
                </div>
                <div className="w-16 h-2 bg-gray-200 rounded-full overflow-hidden">
                  <div
                    className={`h-full ${getSimilarityColor(doc.similarity)} transition-all`}
                    style={{ width: `${doc.similarity * 100}%` }}
                  />
                </div>
              </div>
            </div>
            {doc.content_summary && (
              <p className="text-sm text-gray-600 line-clamp-2 mt-2">
                {doc.content_summary}
              </p>
            )}
          </div>
        ))}
      </div>
      {similarDocs.total > similarDocs.items.length && (
        <div className="mt-4 text-sm text-gray-500 text-center">
          显示 {similarDocs.items.length} / {similarDocs.total} 个相似文档
        </div>
      )}
    </Card>
  )
}


