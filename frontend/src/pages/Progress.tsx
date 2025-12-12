import { useEffect, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import Card from '../components/ui/Card'
import ProgressBar from '../components/ui/ProgressBar'
import LoadingSpinner from '../components/ui/LoadingSpinner'
import { documentsApi } from '../api/documents'
import type { DocumentProgressResponse } from '../types'

export default function Progress() {
  const { documentId } = useParams<{ documentId: string }>()
  const navigate = useNavigate()
  const [progress, setProgress] = useState<DocumentProgressResponse | null>(null)
  const [error, setError] = useState<string | null>(null)

  // 获取初始进度
  useEffect(() => {
    if (!documentId) return

    const fetchProgress = async () => {
      try {
        const data = await documentsApi.getProgress(documentId)
        setProgress(data)
        
        // 如果已完成，跳转到结果页面
        if (data.status === 'completed') {
          navigate(`/result/${documentId}`)
        }
      } catch (err: any) {
        setError(err.response?.data?.detail || '获取进度失败')
      }
    }

    fetchProgress()
    const interval = setInterval(fetchProgress, 2000) // 每2秒轮询一次

    return () => clearInterval(interval)
  }, [documentId, navigate])

  // 注意：WebSocket需要task_id，目前使用轮询方式获取进度
  // 未来可以优化为从上传响应中获取task_id并建立WebSocket连接

  if (error) {
    return (
      <div className="max-w-3xl mx-auto">
        <Card>
          <div className="text-center">
            <div className="text-red-600 mb-4">{error}</div>
            <button
              onClick={() => navigate('/')}
              className="text-primary-600 hover:text-primary-700"
            >
              返回首页
            </button>
          </div>
        </Card>
      </div>
    )
  }

  if (!progress) {
    return (
      <div className="max-w-3xl mx-auto">
        <Card>
          <div className="text-center py-8">
            <LoadingSpinner size="lg" />
            <p className="mt-4 text-gray-600">加载中...</p>
          </div>
        </Card>
      </div>
    )
  }

  return (
    <div className="max-w-3xl mx-auto">
      <Card title="处理进度">
        <div className="space-y-6">
          <ProgressBar
            progress={progress.progress}
            currentStage={progress.current_stage}
          />

          <div className="bg-gray-50 rounded-lg p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-600">状态</p>
                <p className="font-medium text-gray-900 capitalize">{progress.status}</p>
              </div>
              <div className="text-right">
                <p className="text-sm text-gray-600">进度</p>
                <p className="font-medium text-gray-900">{progress.progress}%</p>
              </div>
            </div>
          </div>

          {progress.status === 'processing' && (
            <div className="text-center text-sm text-gray-500">
              <p>文档正在处理中，请稍候...</p>
              <p className="mt-2">处理完成后将自动跳转到结果页面</p>
            </div>
          )}
        </div>
      </Card>
    </div>
  )
}

