import { useState, useEffect } from 'react'
import Card from './ui/Card'
import LoadingSpinner from './ui/LoadingSpinner'

interface ProgressiveModuleProps {
  title: string
  icon: string
  description: string
  view: 'learning' | 'qa' | 'system'
  documentId: string
  isPrimary?: boolean
}

/**
 * 渐进式模块组件
 * 实时获取部分结果并展示，支持展开/收起动画
 */
export default function ProgressiveModule({
  title,
  icon,
  description,
  view,
  documentId,
  isPrimary = false
}: ProgressiveModuleProps) {
  const [hasContent, setHasContent] = useState(false)
  const [isExpanded, setIsExpanded] = useState(false)
  const [partialResult, setPartialResult] = useState<any>(null)
  const [isLoading, setIsLoading] = useState(true)

  // 轮询获取部分结果
  useEffect(() => {
    if (!documentId) return

    const fetchPartialResult = async () => {
      try {
        const { documentsApi } = await import('../api/documents')
        const result = await documentsApi.getResult(documentId, view)
        
        // 处理两种响应类型：DocumentResultResponse 或 MultiViewResultResponse
        let resultData: any = null
        
        if ('result' in result && result.result) {
          // DocumentResultResponse 格式
          resultData = result.result
        } else if ('views' in result && result.views && result.views[view]) {
          // MultiViewResultResponse 格式
          resultData = result.views[view]
        }
        
        // 检查是否有内容
        if (resultData && typeof resultData === 'object' && Object.keys(resultData).length > 0) {
          setHasContent(true)
          setPartialResult(resultData)
          setIsExpanded(true) // 有内容时自动展开
          setIsLoading(false)
        } else {
          setIsLoading(true)
        }
      } catch (err: any) {
        // 404 表示结果还未准备好，继续轮询
        if (err.response?.status === 404) {
          setIsLoading(true)
        } else {
          console.error('获取部分结果失败:', err)
          setIsLoading(false)
        }
      }
    }

    // 立即获取一次
    fetchPartialResult()

    // 每2秒轮询一次
    const interval = setInterval(fetchPartialResult, 2000)

    return () => clearInterval(interval)
  }, [documentId, view])

  // 如果没有内容，显示骨架屏
  if (!hasContent) {
    return (
      <div className="relative">
        {isPrimary && (
          <div className="absolute -top-2 -right-2 bg-primary-500 text-white text-xs px-2 py-0.5 rounded-full z-10">
            主视角
          </div>
        )}
        <Card>
          <div className="space-y-4">
            <div className="flex items-center space-x-2">
              <span className="text-2xl">{icon}</span>
              <h3 className="text-lg font-medium text-gray-900">{title}</h3>
            </div>
            <p className="text-sm text-gray-600">{description}</p>
            <div className="space-y-3 animate-pulse">
              <div className="h-4 bg-gray-200 rounded w-3/4"></div>
              <div className="h-4 bg-gray-200 rounded w-full"></div>
              <div className="h-4 bg-gray-200 rounded w-5/6"></div>
            </div>
            <div className="flex items-center space-x-2 text-sm text-gray-500">
              <div className="w-4 h-4 border-2 border-primary-500 border-t-transparent rounded-full animate-spin"></div>
              <span>正在生成...</span>
            </div>
          </div>
        </Card>
      </div>
    )
  }

  // 有内容时，显示部分结果预览
  return (
    <div className="relative">
      {isPrimary && (
        <div className="absolute -top-2 -right-2 bg-primary-500 text-white text-xs px-2 py-0.5 rounded-full z-10">
          主视角
        </div>
      )}
      <Card>
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-2">
              <span className="text-2xl">{icon}</span>
              <h3 className="text-lg font-medium text-gray-900">{title}</h3>
            </div>
            <button
              onClick={() => setIsExpanded(!isExpanded)}
              className="text-sm text-primary-600 hover:text-primary-700 transition-colors"
            >
              {isExpanded ? '收起' : '展开'}
            </button>
          </div>

          {isExpanded && partialResult && (
            <div className="mt-4 space-y-3 animate-fade-in">
              {/* 根据view类型显示不同的预览内容 */}
              {view === 'learning' && (
                <>
                  {partialResult.prerequisites && (
                    <div className="bg-blue-50 border border-blue-200 rounded-lg p-3">
                      <p className="text-sm font-medium text-blue-900 mb-1">前置条件</p>
                      <p className="text-xs text-blue-700">
                        {Array.isArray(partialResult.prerequisites?.required) 
                          ? `${partialResult.prerequisites.required.length} 个必需条件`
                          : '正在生成...'}
                      </p>
                    </div>
                  )}
                  {partialResult.learning_path && (
                    <div className="bg-green-50 border border-green-200 rounded-lg p-3">
                      <p className="text-sm font-medium text-green-900 mb-1">学习路径</p>
                      <p className="text-xs text-green-700">
                        {Array.isArray(partialResult.learning_path)
                          ? `${partialResult.learning_path.length} 个学习阶段`
                          : '正在生成...'}
                      </p>
                    </div>
                  )}
                </>
              )}

              {view === 'qa' && (
                <>
                  {partialResult.summary && (
                    <div className="bg-purple-50 border border-purple-200 rounded-lg p-3">
                      <p className="text-sm font-medium text-purple-900 mb-1">内容总结</p>
                      <p className="text-xs text-purple-700">
                        {partialResult.summary?.key_points?.length 
                          ? `${partialResult.summary.key_points.length} 个关键点`
                          : '正在生成...'}
                      </p>
                    </div>
                  )}
                  {partialResult.generated_questions && (
                    <div className="bg-orange-50 border border-orange-200 rounded-lg p-3">
                      <p className="text-sm font-medium text-orange-900 mb-1">问题列表</p>
                      <p className="text-xs text-orange-700">
                        {Array.isArray(partialResult.generated_questions)
                          ? `${partialResult.generated_questions.length} 个问题`
                          : '正在生成...'}
                      </p>
                    </div>
                  )}
                </>
              )}

              {view === 'system' && (
                <>
                  {partialResult.config_steps && (
                    <div className="bg-indigo-50 border border-indigo-200 rounded-lg p-3">
                      <p className="text-sm font-medium text-indigo-900 mb-1">配置流程</p>
                      <p className="text-xs text-indigo-700">
                        {Array.isArray(partialResult.config_steps)
                          ? `${partialResult.config_steps.length} 个配置步骤`
                          : '正在生成...'}
                      </p>
                    </div>
                  )}
                  {partialResult.components && (
                    <div className="bg-teal-50 border border-teal-200 rounded-lg p-3">
                      <p className="text-sm font-medium text-teal-900 mb-1">系统组件</p>
                      <p className="text-xs text-teal-700">
                        {Array.isArray(partialResult.components)
                          ? `${partialResult.components.length} 个组件`
                          : '正在生成...'}
                      </p>
                    </div>
                  )}
                </>
              )}

              {/* 如果还在处理中，显示加载提示 */}
              {isLoading && (
                <div className="flex items-center space-x-2 text-sm text-gray-500">
                  <LoadingSpinner size="sm" />
                  <span>正在生成更多内容...</span>
                </div>
              )}
            </div>
          )}

          {!isExpanded && (
            <div className="mt-2 text-sm text-gray-500">
              点击展开查看已生成的内容
            </div>
          )}
        </div>
      </Card>
    </div>
  )
}

