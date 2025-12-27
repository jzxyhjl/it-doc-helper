/**
 * 视角选择组件
 * 支持主次视角显示和切换
 */
import { useState, useEffect } from 'react'
import Button from './ui/Button'
import Card from './ui/Card'
import LoadingSpinner from './ui/LoadingSpinner'
import { documentsApi } from '../api/documents'

export type ViewType = 'learning' | 'qa' | 'system'

interface ViewInfo {
  id: ViewType
  name: string
  icon: string
  description: string
}

const VIEW_INFO: Record<ViewType, ViewInfo> = {
  learning: {
    id: 'learning',
    name: '学习视角',
    icon: '📚',
    description: '帮你梳理学习路径和方法建议'
  },
  qa: {
    id: 'qa',
    name: '问答视角',
    icon: '❓',
    description: '帮你整理问答和知识点总结'
  },
  system: {
    id: 'system',
    name: '系统视角',
    icon: '🏗️',
    description: '帮你理解系统组件和配置流程'
  }
}

interface PerspectiveSelectorProps {
  documentId: string
  primaryView?: ViewType
  enabledViews?: ViewType[]
  currentView?: ViewType
  viewsStatus?: {
    views_status: Record<string, {
      has_content?: boolean
      status?: string
      ready?: boolean  // 视角是否已完成（ready: true 表示已完成）
    }>
  }
  onViewChange?: (view: ViewType) => void
  onRecommendationChange?: (primaryView: ViewType, enabledViews: ViewType[]) => void
}

export default function PerspectiveSelector({
  documentId,
  primaryView,
  enabledViews = [],
  currentView,
  viewsStatus,
  onViewChange,
  onRecommendationChange
}: PerspectiveSelectorProps) {
  const [recommendation, setRecommendation] = useState<{
    primary_view: ViewType
    enabled_views: ViewType[]
    detection_scores: Record<ViewType, number>
  } | null>(null)
  const [loading, setLoading] = useState(false)
  const [switching, setSwitching] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // 获取推荐视角（如果已经有primaryView和enabledViews，就不需要获取推荐）
  useEffect(() => {
    const fetchRecommendation = async () => {
      if (!documentId) return
      
      // 如果已经有primaryView和enabledViews，就不需要获取推荐
      if (primaryView && enabledViews && enabledViews.length > 0) {
        setLoading(false)
        return
      }

      setLoading(true)
      setError(null)

      try {
        const data = await documentsApi.recommendViews(documentId)
        // 类型转换：API 返回的是 string，需要转换为 ViewType
        const recommendation = {
          primary_view: data.primary_view as ViewType,
          enabled_views: data.enabled_views as ViewType[],
          detection_scores: data.detection_scores as Record<ViewType, number>
        }
        setRecommendation(recommendation)

        // 通知父组件推荐结果
        if (onRecommendationChange) {
          onRecommendationChange(recommendation.primary_view, recommendation.enabled_views)
        }
      } catch (err: any) {
        console.error('获取推荐视角失败:', err)
        // 如果文档还在处理中，返回404是正常的，不需要显示错误
        if (err.response?.status === 404) {
          setLoading(false)
          return
        }
        // 只在非404错误时显示错误信息
        if (err.message && !err.message.includes('404') && !err.message.includes('Failed to fetch')) {
          setError(err.message || '获取推荐视角失败')
        }
      } finally {
        setLoading(false)
      }
    }

    fetchRecommendation()
  }, [documentId, onRecommendationChange, primaryView, enabledViews])

  // 切换视角
  const handleSwitchView = async (targetView: ViewType) => {
    if (targetView === currentView || switching) return

    setSwitching(true)
    setError(null)

    try {
      // 调用切换视角接口
      await documentsApi.switchView(documentId, targetView)

      // 通知父组件视角已切换
      if (onViewChange) {
        onViewChange(targetView)
      }
    } catch (err: any) {
      console.error('切换视角失败:', err)
      setError(err.message || '切换视角失败')
    } finally {
      // 延迟一下，让用户看到切换提示
      setTimeout(() => {
        setSwitching(false)
      }, 1000)
    }
  }

  // 使用推荐结果或传入的props
  const displayPrimaryView = primaryView || recommendation?.primary_view
  const displayEnabledViews = enabledViews.length > 0 ? enabledViews : (recommendation?.enabled_views || [])

  if (loading) {
    return (
      <Card>
        <div className="text-center py-4">
          <LoadingSpinner size="sm" />
          <p className="mt-2 text-sm text-gray-600">正在获取推荐视角...</p>
        </div>
      </Card>
    )
  }

  return (
    <Card>
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <h3 className="text-lg font-semibold text-gray-900">选择视角</h3>
          {switching && (
            <div className="flex items-center text-sm text-primary-600">
              <LoadingSpinner size="sm" />
              <span className="ml-2">正在切换视角，预计5秒内完成...</span>
            </div>
          )}
        </div>

        {error && (
          <div className="bg-red-50 border border-red-200 rounded-md p-3">
            <p className="text-sm text-red-600">{error}</p>
          </div>
        )}

        {/* 主视角 - 只显示已完成的 */}
        {displayPrimaryView && (() => {
          // 检查主视角是否已完成
          const primaryViewStatus = viewsStatus?.views_status[displayPrimaryView]
          const isPrimaryReady = primaryViewStatus?.ready !== false  // 如果没有状态信息，默认显示（向后兼容）
          
          // 如果主视角未完成，不显示
          if (primaryViewStatus && !isPrimaryReady) {
            return null
          }
          
          return (
            <div>
              <p className="text-sm font-medium text-gray-700 mb-2">主推荐视角</p>
              <div className="flex items-center space-x-2">
                <button
                  onClick={() => handleSwitchView(displayPrimaryView)}
                  disabled={switching || currentView === displayPrimaryView}
                  className={`flex-1 flex items-center space-x-3 p-3 rounded-lg border-2 transition-all ${
                    currentView === displayPrimaryView
                      ? 'border-primary-500 bg-primary-50'
                      : 'border-gray-200 hover:border-primary-300 hover:bg-gray-50'
                  } ${switching ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'}`}
                >
                  <span className="text-2xl">{VIEW_INFO[displayPrimaryView].icon}</span>
                  <div className="flex-1 text-left">
                    <p className="font-medium text-gray-900">{VIEW_INFO[displayPrimaryView].name}</p>
                    <p className="text-xs text-gray-500">{VIEW_INFO[displayPrimaryView].description}</p>
                  </div>
                  {currentView === displayPrimaryView && (
                    <span className="text-primary-600 text-sm font-medium">当前</span>
                  )}
                </button>
              </div>
            </div>
          )
        })()}

        {/* 次视角 */}
        {displayEnabledViews.length > 1 && (
          <div>
            <p className="text-sm font-medium text-gray-700 mb-2">可选视角</p>
            <div className="grid grid-cols-1 gap-2">
              {displayEnabledViews
                .filter((view) => {
                  // 过滤掉主视角
                  if (view === displayPrimaryView) return false
                  // 如果提供了 viewsStatus，检查是否已完成（ready: true）
                  if (viewsStatus?.views_status[view]) {
                    const viewStatus = viewsStatus.views_status[view]
                    // 如果 ready 为 false 或未定义，不显示该视角按钮（只显示已完成的）
                    if (viewStatus.ready === false) return false
                    // 如果 status 是 processing 或 pending，也不显示
                    if (viewStatus.status === 'processing' || viewStatus.status === 'pending') return false
                  }
                  // 如果没有状态信息，默认显示（向后兼容）
                  return true
                })
                .map((view) => (
                  <button
                    key={view}
                    onClick={() => handleSwitchView(view)}
                    disabled={switching || currentView === view}
                    className={`flex items-center space-x-3 p-3 rounded-lg border transition-all ${
                      currentView === view
                        ? 'border-primary-500 bg-primary-50'
                        : 'border-gray-200 hover:border-primary-300 hover:bg-gray-50'
                    } ${switching ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'}`}
                  >
                    <span className="text-xl">{VIEW_INFO[view].icon}</span>
                    <div className="flex-1 text-left">
                      <p className="font-medium text-gray-900">{VIEW_INFO[view].name}</p>
                      <p className="text-xs text-gray-500">{VIEW_INFO[view].description}</p>
                    </div>
                    {currentView === view && (
                      <span className="text-primary-600 text-sm font-medium">当前</span>
                    )}
                    {recommendation?.detection_scores?.[view] !== undefined && (
                      <span className="text-xs text-gray-400">
                        {Math.round(recommendation.detection_scores[view] * 100)}%
                      </span>
                    )}
                  </button>
                ))}
            </div>
          </div>
        )}

        {/* 检测得分（可选显示） */}
        {recommendation?.detection_scores && (
          <div className="pt-3 border-t border-gray-200">
            <details className="text-sm">
              <summary className="cursor-pointer text-gray-600 hover:text-gray-900">
                查看检测得分
              </summary>
              <div className="mt-2 space-y-1">
                {Object.entries(recommendation.detection_scores).map(([view, score]) => (
                  <div key={view} className="flex items-center justify-between">
                    <span className="text-gray-600">{VIEW_INFO[view as ViewType].name}:</span>
                    <span className="font-medium text-gray-900">
                      {Math.round(score * 100)}%
                    </span>
                  </div>
                ))}
              </div>
            </details>
          </div>
        )}
      </div>
    </Card>
  )
}

