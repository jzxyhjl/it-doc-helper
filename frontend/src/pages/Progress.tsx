import { useEffect, useState, useRef } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import Card from '../components/ui/Card'
import ProgressBar from '../components/ui/ProgressBar'
import LoadingSpinner from '../components/ui/LoadingSpinner'
import ProgressModuleSkeleton from '../components/ProgressModuleSkeleton'
import ProgressiveModule from '../components/ProgressiveModule'
import StreamingContent from '../components/StreamingContent'
import { documentsApi } from '../api/documents'
import { useDocumentStore } from '../store/documentStore'
import { useWebSocket } from '../hooks/useWebSocket'
import type { DocumentProgressResponse } from '../types'

export default function Progress() {
  const { documentId } = useParams<{ documentId: string }>()
  const navigate = useNavigate()
  const [progress, setProgress] = useState<DocumentProgressResponse | null>(null)
  const [error, setError] = useState<string | null>(null)
  
  // 获取task_id（优先从progress响应中获取，否则从store获取）
  const { currentTaskId } = useDocumentStore()
  const taskId = progress?.task_id || currentTaskId
  
  // 流式内容状态：按view和module组织
  const [streamingContent, setStreamingContent] = useState<Record<string, Record<string, string>>>({})
  
  // WebSocket连接（如果有task_id）
  const wsUrl = taskId 
    ? `/api/v1/ws/progress/${taskId}`
    : null
  
  // 处理WebSocket消息
  const handleWebSocketMessage = (data: any) => {
    // 处理进度更新
    if (data.progress !== undefined || data.stage || data.status) {
      setProgress(prev => ({
        ...prev!,
        progress: data.progress ?? prev?.progress ?? 0,
        current_stage: data.stage ?? prev?.current_stage,
        status: data.status ?? prev?.status ?? 'running',
        enabled_views: data.enabled_views ?? prev?.enabled_views,
        primary_view: data.primary_view ?? prev?.primary_view,
        task_id: data.task_id ?? prev?.task_id
      }))
    }
    
    // 处理流式内容
    if (data.type === 'stream' && data.stream) {
      const { view, module, chunk } = data.stream
      if (view && module && chunk) {
        setStreamingContent(prev => {
          const viewContent = prev[view] || {}
          const moduleContent = viewContent[module] || ''
          return {
            ...prev,
            [view]: {
              ...viewContent,
              [module]: moduleContent + chunk
            }
          }
        })
      }
    }
  }
  
  // 建立WebSocket连接
  const { isConnected } = useWebSocket({
    url: wsUrl || '',
    onMessage: handleWebSocketMessage,
    onError: (err) => {
      console.error('WebSocket错误:', err)
    },
    onClose: () => {
      console.log('WebSocket连接关闭')
    }
  })

  // 获取初始进度
  useEffect(() => {
    if (!documentId) return

    const fetchProgress = async () => {
      try {
        const data = await documentsApi.getProgress(documentId)
        setProgress(data)
        
        // 如果已完成，等待一下确保数据已保存，然后跳转到结果页面
        if (data.status === 'completed') {
          // 等待500ms确保后端数据已完全保存
          await new Promise(resolve => setTimeout(resolve, 500))
          
          // 验证结果是否已准备好
          try {
            const resultData = await documentsApi.getResult(documentId)
            // 如果结果存在，跳转到结果页面
            if (resultData) {
              navigate(`/result/${documentId}`)
            }
          } catch (err: any) {
            // 如果结果还没准备好，继续等待
            console.log('结果还未准备好，继续等待...', err)
          }
        }
      } catch (err: any) {
        setError(err.response?.data?.detail || '获取进度失败')
      }
    }

    fetchProgress()
    // 如果WebSocket未连接，使用轮询作为后备方案
    if (!isConnected) {
      const interval = setInterval(fetchProgress, 2000) // 每2秒轮询一次
      return () => clearInterval(interval)
    }
  }, [documentId, navigate, isConnected])

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
      <Card title="分析进度">
        <div className="space-y-6">
          <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
            <p className="text-sm text-blue-800">
              📝 正在分析文档结构，稍后会生成初步学习路线（你可以随时调整）
            </p>
          </div>

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

          {/* 根据视角动态展示模块（渐进式反馈 + 流式内容） */}
          {progress.status === 'processing' && progress.enabled_views && progress.enabled_views.length > 0 && (
            <div className="space-y-4">
              <div className="text-sm text-gray-600 mb-4">
                <p className="font-medium">检测到的视角：</p>
                <p className="text-xs text-gray-500 mt-1">
                  {progress.enabled_views.length === 1 
                    ? '正在生成一个视角的内容' 
                    : `正在生成 ${progress.enabled_views.length} 个视角的内容`}
                  {isConnected && (
                    <span className="ml-2 text-green-600">● 实时连接中</span>
                  )}
                </p>
              </div>
              
              <div className="grid grid-cols-1 gap-4">
                {progress.enabled_views.map((view) => {
                  const isPrimary = view === progress.primary_view
                  let moduleInfo: { title: string; icon: string; description: string } | null = null
                  
                  if (view === 'learning') {
                    moduleInfo = {
                      title: '学习视角',
                      icon: '📚',
                      description: '正在生成学习路径和方法建议...'
                    }
                  } else if (view === 'qa') {
                    moduleInfo = {
                      title: '问答视角',
                      icon: '❓',
                      description: '正在整理问答和知识点总结...'
                    }
                  } else if (view === 'system') {
                    moduleInfo = {
                      title: '系统视角',
                      icon: '🏗️',
                      description: '正在理解系统组件和配置流程...'
                    }
                  }
                  
                  if (!moduleInfo) return null
                  
                  // 获取该视角的流式内容
                  const viewStreaming = streamingContent[view] || {}
                  
                  // 使用渐进式模块组件（会自动轮询获取部分结果）
                  return (
                    <div key={view} className="space-y-2">
                      <ProgressiveModule
                        title={moduleInfo.title}
                        icon={moduleInfo.icon}
                        description={moduleInfo.description}
                        view={view as 'learning' | 'qa' | 'system'}
                        documentId={documentId!}
                        isPrimary={isPrimary}
                      />
                      
                      {/* 显示流式内容（如果有） */}
                      {Object.keys(viewStreaming).length > 0 && (
                        <Card className="bg-gray-50">
                          <div className="space-y-2">
                            {Object.entries(viewStreaming).map(([module, content]) => (
                              <div key={module} className="border-b border-gray-200 pb-2 last:border-0">
                                <p className="text-xs font-medium text-gray-600 mb-1 capitalize">
                                  {module === 'prerequisites' ? '前置条件' :
                                   module === 'learning_path' ? '学习路径' :
                                   module === 'summary' ? '内容总结' :
                                   module === 'generated_questions' ? '问题生成' :
                                   module === 'config_steps' ? '配置流程' :
                                   module === 'components' ? '系统组件' :
                                   module}
                                </p>
                                <StreamingContent
                                  view={view}
                                  module={module}
                                  content={content}
                                />
                              </div>
                            ))}
                          </div>
                        </Card>
                      )}
                    </div>
                  )
                })}
              </div>
            </div>
          )}
          
          {/* 如果还没有检测到视角，显示通用提示 */}
          {progress.status === 'processing' && (!progress.enabled_views || progress.enabled_views.length === 0) && (
            <div className="text-center text-sm text-gray-500">
              <p>正在分析文档结构，请稍候...</p>
              <p className="mt-2">完成后将显示初步的学习路线，你可以进一步调整</p>
            </div>
          )}
        </div>
      </Card>
    </div>
  )
}
