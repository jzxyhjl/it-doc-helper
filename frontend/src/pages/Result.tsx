import { useEffect, useState, useRef } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import Card from '../components/ui/Card'
import Button from '../components/ui/Button'
import LoadingSpinner from '../components/ui/LoadingSpinner'
import Recommendations from '../components/Recommendations'
import MermaidRenderer from '../components/MermaidRenderer'
import ErrorBoundary from '../components/ErrorBoundary'
import ConfidenceBadge from '../components/ConfidenceBadge'
import SourceList from '../components/SourceList'
import PerspectiveSelector, { ViewType } from '../components/PerspectiveSelector'
import { documentsApi } from '../api/documents'
import type { DocumentResultResponse, MultiViewResultResponse, ViewsStatusResponse } from '../types'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'

export default function Result() {
  const { documentId } = useParams<{ documentId: string }>()
  const navigate = useNavigate()
  const [result, setResult] = useState<DocumentResultResponse | null>(null)
  const [multiViewResult, setMultiViewResult] = useState<MultiViewResultResponse | null>(null)
  const [viewsStatus, setViewsStatus] = useState<ViewsStatusResponse | null>(null)
  const [currentView, setCurrentView] = useState<ViewType | null>(null)
  const [primaryView, setPrimaryView] = useState<ViewType | null>(null)
  const [enabledViews, setEnabledViews] = useState<ViewType[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const pollingIntervalRef = useRef<number | null>(null)

  // 获取多视角结果和状态
  useEffect(() => {
    if (!documentId) return

    const fetchResults = async (retryCount = 0) => {
      try {
        // 1. 先获取完整的多视角容器（不指定view）
        try {
          const multiViewData = await documentsApi.getResult(documentId) as any
          
          console.log('获取到的数据:', {
            hasViews: 'views' in multiViewData,
            viewsType: typeof multiViewData?.views,
            viewsIsArray: Array.isArray(multiViewData?.views),
            viewsKeys: multiViewData?.views ? Object.keys(multiViewData.views) : [],
            hasMeta: 'meta' in multiViewData,
            metaPrimaryView: multiViewData?.meta?.primary_view
          })
          
          // 检查是否是多视角容器格式（后端返回的是 views 字典，不是 results）
          if ('views' in multiViewData && typeof multiViewData.views === 'object' && !Array.isArray(multiViewData.views)) {
            setMultiViewResult(multiViewData)
            
            // 从meta中获取primary_view和enabled_views
            const meta = multiViewData.meta
            if (meta?.enabled_views) {
              setEnabledViews(meta.enabled_views as ViewType[])
            }
            
            // 获取主视角
            const primary = meta?.primary_view || (Object.keys(multiViewData.views || {})[0] as ViewType | undefined)
            
            if (primary) {
              setPrimaryView(primary)
              setCurrentView(primary)
              
              // 获取主视角结果（从views字典中获取，不是results）
              const primaryResult = multiViewData.views[primary]
              console.log('主视角结果检查:', {
                primary,
                viewsKeys: Object.keys(multiViewData.views || {}),
                primaryResultExists: !!primaryResult,
                primaryResultKeys: primaryResult ? Object.keys(primaryResult) : [],
                primaryResultType: typeof primaryResult
              })
              
              if (primaryResult && typeof primaryResult === 'object' && Object.keys(primaryResult).length > 0) {
                // 确保结果不为空
                const resultData = {
                  document_id: documentId,
                  document_type: getDocumentTypeFromView(primary),
                  result: primaryResult,
                  created_at: new Date().toISOString()
                }
                console.log('设置result state:', {
                  document_id: resultData.document_id,
                  document_type: resultData.document_type,
                  resultKeys: Object.keys(resultData.result),
                  primary
                })
                setResult(resultData)
              } else {
                // 如果主视角结果不存在或为空，尝试使用第一个可用的view
                console.warn('主视角结果不存在或为空，尝试使用第一个可用的view', { 
                  primary, 
                  views: Object.keys(multiViewData.views || {}),
                  primaryResult
                })
                const views = multiViewData.views || {}
                const firstView = Object.keys(views).find(v => views[v] && typeof views[v] === 'object' && Object.keys(views[v]).length > 0) as ViewType | undefined
                if (firstView && views[firstView]) {
                  setPrimaryView(firstView)
                  setCurrentView(firstView)
                  setResult({
                    document_id: documentId,
                    document_type: getDocumentTypeFromView(firstView),
                    result: views[firstView],
                    created_at: new Date().toISOString()
                  })
                } else if (retryCount < 3) {
                  // 如果所有view的结果都为空，可能是数据还没完全保存，重试
                  console.log(`结果为空，${500 * (retryCount + 1)}ms后重试...`)
                  await new Promise(resolve => setTimeout(resolve, 500 * (retryCount + 1)))
                  return fetchResults(retryCount + 1)
                }
              }
            } else {
              // 如果没有可用的view，可能是数据还没准备好
              if (retryCount < 3) {
                console.log(`没有可用的view，${500 * (retryCount + 1)}ms后重试...`)
                await new Promise(resolve => setTimeout(resolve, 500 * (retryCount + 1)))
                return fetchResults(retryCount + 1)
              }
            }
          } else {
            // 旧格式，直接使用
            console.log('使用旧格式数据', multiViewData)
            setResult(multiViewData)
          }
        } catch (err: any) {
          console.error('获取结果失败:', err)
          if (err.response?.status === 404) {
            // 文档可能还在处理中，尝试获取状态
            if (retryCount < 5) {
              // 404时重试，最多5次
              console.log(`404错误，${1000 * (retryCount + 1)}ms后重试...`)
              await new Promise(resolve => setTimeout(resolve, 1000 * (retryCount + 1)))
              return fetchResults(retryCount + 1)
            }
            await fetchViewsStatus()
            return
          }
          throw err
        }

        // 2. 获取视角状态（用于轮询）
        await fetchViewsStatus()
      } catch (err: any) {
        setError(err.response?.data?.detail || '获取结果失败')
      } finally {
        setLoading(false)
      }
    }

    fetchResults()
  }, [documentId])

  // 获取视角状态
  const fetchViewsStatus = async () => {
    if (!documentId) return

    try {
      const status = await documentsApi.getViewsStatus(documentId)
      setViewsStatus(status)

      // 设置primary_view和enabled_views
      if (status.primary_view) {
        setPrimaryView(status.primary_view as ViewType)
        if (!currentView) {
          setCurrentView(status.primary_view as ViewType)
        }
      }
      if (status.enabled_views) {
        setEnabledViews(status.enabled_views as ViewType[])
      }

      // 检查是否有正在处理的视角
      const hasProcessing = Object.values(status.views_status).some(
        (viewStatus) => viewStatus.status === 'processing' || viewStatus.status === 'pending'
      )

      // 如果有正在处理的视角，启动轮询
      if (hasProcessing) {
        startPolling()
      } else {
        stopPolling()
        
        // 如果所有视角都完成了，但还没有结果，尝试重新获取结果
        if (!result && status.primary_view) {
          try {
            const multiViewData = await documentsApi.getResult(documentId)
            if ('views' in multiViewData && typeof (multiViewData as any).views === 'object') {
              const primaryResult = (multiViewData as any).views[status.primary_view]
              if (primaryResult) {
                setResult({
                  document_id: documentId,
                  document_type: getDocumentTypeFromView(status.primary_view as ViewType),
                  result: primaryResult,
                  created_at: new Date().toISOString()
                })
              } else {
                // 如果主视角结果不存在，尝试使用第一个可用的view
                const views = (multiViewData as any).views || {}
                const firstView = Object.keys(views)[0] as ViewType | undefined
                if (firstView && views[firstView]) {
                  setPrimaryView(firstView)
                  setCurrentView(firstView)
                  setResult({
                    document_id: documentId,
                    document_type: getDocumentTypeFromView(firstView),
                    result: views[firstView],
                    created_at: new Date().toISOString()
                  })
                }
              }
            }
          } catch (err) {
            console.error('重新获取结果失败:', err)
          }
        }
      }
    } catch (err: any) {
      console.error('获取视角状态失败:', err)
    }
  }

  // 启动轮询（每2秒）
  const startPolling = () => {
    if (pollingIntervalRef.current) return

    pollingIntervalRef.current = setInterval(() => {
      fetchViewsStatus()
    }, 2000)
  }

  // 停止轮询
  const stopPolling = () => {
    if (pollingIntervalRef.current) {
      clearInterval(pollingIntervalRef.current)
      pollingIntervalRef.current = null
    }
  }

  // 清理轮询
  useEffect(() => {
    return () => {
      stopPolling()
    }
  }, [])

  // 切换视角
  const handleExport = async () => {
    if (!documentId || !currentView) {
      alert('无法导出：缺少文档ID或视角信息')
      return
    }

    try {
      const response = await fetch(`/api/v1/documents/${documentId}/export?view=${currentView}&format=markdown`, {
        method: 'GET',
        headers: {
          'Accept': 'text/markdown'
        }
      })

      if (!response.ok) {
        throw new Error(`导出失败: ${response.statusText}`)
      }

      const blob = await response.blob()
      const url = window.URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      
      // 从Content-Disposition头获取文件名，或使用默认名称
      const contentDisposition = response.headers.get('Content-Disposition')
      let filename = `result_${currentView}_${new Date().toISOString().slice(0, 10)}.md`
      if (contentDisposition) {
        const filenameMatch = contentDisposition.match(/filename="?([^"]+)"?/)
        if (filenameMatch) {
          filename = filenameMatch[1]
        }
      }
      
      a.download = filename
      document.body.appendChild(a)
      a.click()
      window.URL.revokeObjectURL(url)
      document.body.removeChild(a)
    } catch (err: any) {
      console.error('导出失败:', err)
      alert(`导出失败: ${err.message || '未知错误'}`)
    }
  }

  const handleViewChange = async (view: ViewType) => {
    if (!documentId) return

    setCurrentView(view)

    try {
      // 如果多视角结果中已有该视角的结果，直接使用（后端返回的是views字典，不是results）
      if (multiViewResult?.views && (multiViewResult.views as any)[view]) {
        setResult({
          document_id: documentId,
          document_type: getDocumentTypeFromView(view),
          result: (multiViewResult.views as any)[view],
          created_at: new Date().toISOString()
        })
        return
      }

      // 否则调用切换视角接口
      const data = await documentsApi.switchView(documentId, view)
      setResult(data)
    } catch (err: any) {
      console.error('切换视角失败:', err)
      setError(err.response?.data?.detail || '切换视角失败')
    }
  }

  // 从view获取document_type（向后兼容）
  const getDocumentTypeFromView = (view: ViewType): string => {
    const mapping: Record<ViewType, string> = {
      learning: 'technical',
      qa: 'interview',
      system: 'architecture'
    }
    return mapping[view] || 'unknown'
  }

  const renderResult = () => {
    if (!result) {
      console.warn('renderResult: result is null')
      return null
    }

    const { document_type, result: resultData } = result

    console.log('renderResult 被调用:', {
      hasResult: !!result,
      document_type,
      resultDataKeys: resultData ? Object.keys(resultData) : [],
      resultDataType: typeof resultData
    })

    // 数据验证和异常处理
    if (!resultData) {
      console.warn('renderResult: resultData is null or undefined')
      return (
        <Card>
          <div className="text-center py-8">
            <p className="text-red-600 mb-4">处理结果数据为空</p>
            <p className="text-sm text-gray-500">文档可能还在处理中，请稍后重试</p>
          </div>
        </Card>
      )
    }

    try {
      console.log('准备渲染组件，document_type:', document_type)
      if (document_type === 'interview') {
        return <InterviewResult data={resultData} />
      } else if (document_type === 'technical') {
        return <TechnicalResult data={resultData} />
      } else if (document_type === 'architecture') {
        console.log('渲染 ArchitectureResult，数据keys:', Object.keys(resultData))
        return <ArchitectureResult data={resultData} />
      }

      console.warn('未知的文档类型:', document_type)
      return <div className="text-gray-600">未知的文档类型: {document_type}</div>
    } catch (err: any) {
      console.error('渲染结果时出错:', err)
      return (
        <Card>
          <div className="text-center py-8">
            <p className="text-red-600 mb-4">结果展示失败</p>
            <p className="text-sm text-gray-500">{err.message || '未知错误'}</p>
            <pre className="mt-4 text-xs text-left overflow-auto">{err.stack}</pre>
          </div>
        </Card>
      )
    }
  }

  if (loading) {
    return (
      <div className="max-w-4xl mx-auto">
        <Card>
          <div className="text-center py-8">
            <LoadingSpinner size="lg" />
            <p className="mt-4 text-gray-600">加载中...</p>
          </div>
        </Card>
      </div>
    )
  }

  if (error) {
    return (
      <div className="max-w-4xl mx-auto">
        <Card>
          <div className="text-center py-8">
            <p className="text-red-600 mb-4">{error}</p>
            <div className="space-x-4">
              <Button onClick={() => navigate('/')}>返回首页</Button>
              {documentId && (
                <Button variant="secondary" onClick={() => navigate(`/progress/${documentId}`)}>
                  查看进度
                </Button>
              )}
            </div>
          </div>
        </Card>
      </div>
    )
  }

  return (
    <div className="max-w-6xl mx-auto space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-2xl font-bold text-gray-900">处理结果</h2>
        <div className="space-x-2">
          <Button 
            variant="secondary" 
            onClick={handleExport}
            disabled={!result || !currentView}
          >
            📥 导出结果
          </Button>
          <Button variant="secondary" onClick={() => navigate('/')}>
            返回首页
          </Button>
          <Button variant="secondary" onClick={() => navigate('/history')}>
            查看历史
          </Button>
        </div>
      </div>

      {/* 视角选择器 - 只在有数据时显示 */}
      {documentId && (primaryView || enabledViews.length > 0) && (
        <PerspectiveSelector
          documentId={documentId}
          primaryView={primaryView || undefined}
          enabledViews={enabledViews}
          currentView={currentView || undefined}
          viewsStatus={viewsStatus || undefined}
          onViewChange={handleViewChange}
          onRecommendationChange={(primary, enabled) => {
            setPrimaryView(primary)
            setEnabledViews(enabled)
            if (!currentView) {
              setCurrentView(primary)
            }
          }}
        />
      )}

      {/* 主视角结果 */}
      {(currentView || result) && (
        <div className="space-y-6">
          <div className="flex items-center justify-between">
            <h3 className="text-lg font-semibold text-gray-900">
              {currentView === 'learning' && '📚 学习视角'}
              {currentView === 'qa' && '❓ 问答视角'}
              {currentView === 'system' && '🏗️ 系统视角'}
              {!currentView && '处理结果'}
            </h3>
            {currentView && viewsStatus?.views_status[currentView]?.status === 'processing' && (
              <div className="flex items-center text-sm text-primary-600">
                <LoadingSpinner size="sm" />
                <span className="ml-2">正在分析，请稍候...</span>
              </div>
            )}
          </div>

          {result ? (
            (() => {
              console.log('准备渲染结果:', {
                hasResult: !!result,
                document_type: result.document_type,
                resultKeys: result.result ? Object.keys(result.result) : [],
                currentView
              })
              return renderResult()
            })()
          ) : (
            <Card>
              <div className="text-center py-8">
                <LoadingSpinner size="lg" />
                <p className="mt-4 text-gray-600">正在获取处理结果...</p>
                {currentView && viewsStatus?.views_status[currentView]?.status === 'completed' && (
                  <p className="mt-2 text-sm text-gray-500">处理已完成，正在加载结果...</p>
                )}
                <div className="mt-4 text-xs text-gray-400">
                  <p>调试信息:</p>
                  <p>currentView: {currentView || 'null'}</p>
                  <p>result: {result ? 'exists' : 'null'}</p>
                  <p>primaryView: {primaryView || 'null'}</p>
                </div>
              </div>
            </Card>
          )}
        </div>
      )}

      {/* 如果没有currentView，显示提示 */}
      {!currentView && !loading && (
        <Card>
          <div className="text-center py-8">
            <LoadingSpinner size="sm" />
            <p className="mt-4 text-gray-600">正在获取视角信息...</p>
          </div>
        </Card>
      )}

      {/* 次视角状态显示 */}
      {viewsStatus && enabledViews.length > 1 && (
        <div className="space-y-4">
          <h3 className="text-lg font-semibold text-gray-900">其他视角</h3>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {enabledViews
              .filter((view) => view !== currentView)
              .map((view) => {
                const viewStatus = viewsStatus.views_status[view]
                const isProcessing = viewStatus?.status === 'processing' || viewStatus?.status === 'pending'
                const isReady = viewStatus?.ready

                return (
                  <Card key={view}>
                    <div className="space-y-2">
                      <div className="flex items-center justify-between">
                        <h4 className="font-medium text-gray-900">
                          {view === 'learning' && '📚 学习视角'}
                          {view === 'qa' && '❓ 问答视角'}
                          {view === 'system' && '🏗️ 系统视角'}
                        </h4>
                        {isProcessing && (
                          <div className="flex items-center text-sm text-primary-600">
                            <LoadingSpinner size="sm" />
                            <span className="ml-1">正在生成...</span>
                          </div>
                        )}
                        {isReady && (
                          <Button
                            size="sm"
                            variant="secondary"
                            onClick={() => handleViewChange(view)}
                          >
                            查看
                          </Button>
                        )}
                      </div>
                      {viewStatus?.processing_time && (
                        <p className="text-xs text-gray-500">
                          处理耗时: {viewStatus.processing_time} 秒
                        </p>
                      )}
                    </div>
                  </Card>
                )
              })}
          </div>
        </div>
      )}

      {/* 相关推荐展示 */}
      {result && (
        <div className="space-y-6">
          <Recommendations documentId={documentId!} limit={3} />
          
          {result.processing_time && (
            <Card>
              <p className="text-sm text-gray-500">
                处理耗时: {result.processing_time} 秒
                {result.quality_score !== undefined && result.quality_score !== null && (
                  <span className="ml-4">
                    质量分数: <span className={`font-semibold ${result.quality_score >= 80 ? 'text-green-600' : result.quality_score >= 60 ? 'text-yellow-600' : 'text-red-600'}`}>
                      {result.quality_score}
                    </span> / 100
                  </span>
                )}
              </p>
            </Card>
          )}
        </div>
      )}
    </div>
  )
}

// 弱展示组件（默认隐藏，可点击展开）
function WeakDisplay({ 
  confidence, 
  confidenceLabel, 
  sources 
}: { 
  confidence?: number
  confidenceLabel?: string
  sources?: Array<{ id: number; text: string; position?: number }>
}) {
  const [isExpanded, setIsExpanded] = useState(false)

  if (confidence === undefined && (!sources || sources.length === 0)) {
    return null
  }

  return (
    <div className="mb-3 border-t border-gray-200 pt-3">
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="flex items-center text-xs text-gray-500 hover:text-gray-700"
      >
        <span className="mr-1">{isExpanded ? '▼' : '▶'}</span>
        <span>查看可信度和来源</span>
      </button>
      
      {isExpanded && (
        <div className="mt-2 space-y-2">
          {confidence !== undefined && (
            <div className="flex items-center gap-2">
              <span className="text-xs text-gray-600">可信度：</span>
              <ConfidenceBadge 
                label={confidenceLabel || '中'} 
                score={confidence}
              />
            </div>
          )}
          {sources && sources.length > 0 && (
            <SourceList sources={sources} collapsed={false} maxLength={200} />
          )}
        </div>
      )}
    </div>
  )
}

// 面试题结果组件（弱展示模式）
function InterviewResult({ data }: { data: any }) {
  return (
    <div className="space-y-6 text-left">
      <Card title="内容总结">
        <div className="space-y-4 text-left">
          {/* 可信度和来源（弱展示：默认隐藏） */}
          {(data.summary?.confidence !== undefined || data.summary?.sources?.length > 0) && (
            <WeakDisplay 
              confidence={data.summary?.confidence}
              confidenceLabel={data.summary?.confidence_label}
              sources={data.summary?.sources}
            />
          )}
          
          {data.summary?.key_points && (
            <div>
              <h4 className="font-medium text-gray-900 mb-2">关键知识点</h4>
              <ul className="list-disc list-inside space-y-1 text-gray-700">
                {data.summary.key_points.map((point: string, index: number) => (
                  <li key={index}>{point}</li>
                ))}
              </ul>
            </div>
          )}
          
          {data.summary?.question_types && (
            <div>
              <h4 className="font-medium text-gray-900 mb-2">题型分布</h4>
              <div className="grid grid-cols-2 gap-4">
                {Object.entries(data.summary.question_types).map(([type, count]: [string, any]) => (
                  <div key={type} className="bg-gray-50 rounded p-2">
                    <span className="text-gray-600">{type}: </span>
                    <span className="font-medium">{count}</span>
                  </div>
                ))}
              </div>
            </div>
          )}
          
          {data.summary?.total_questions && (
            <div>
              <p className="text-gray-600">
                总题目数: <span className="font-medium">{data.summary.total_questions}</span>
              </p>
            </div>
          )}
        </div>
      </Card>

      {data.generated_questions && data.generated_questions.length > 0 && (
        <Card title="生成的问题">
          <div className="space-y-4 text-left">
            {data.generated_questions.map((q: any, index: number) => (
              <div key={index} className="border-l-4 border-primary-500 pl-4 text-left">
                <p className="font-medium text-gray-900 mb-2">{q.question}</p>
                {q.hint && (
                  <p className="text-sm text-gray-600">提示: {q.hint}</p>
                )}
                {/* 可信度和来源（弱展示：默认隐藏） */}
                {(q.confidence !== undefined || q.sources?.length > 0) && (
                  <WeakDisplay 
                    confidence={q.confidence}
                    confidenceLabel={q.confidence_label}
                    sources={q.sources}
                  />
                )}
              </div>
            ))}
          </div>
        </Card>
      )}

      {data.extracted_answers && (
        <Card title="提取的答案">
          {/* 可信度和来源（弱展示：默认隐藏） */}
          {(data.extracted_answers.confidence !== undefined || data.extracted_answers.sources?.length > 0) && (
            <WeakDisplay 
              confidence={data.extracted_answers.confidence}
              confidenceLabel={data.extracted_answers.confidence_label}
              sources={data.extracted_answers.sources}
            />
          )}
          
          {/* 答案列表 */}
          {Array.isArray(data.extracted_answers) && data.extracted_answers.length > 0 && (
            <div className="space-y-2 text-left">
              {data.extracted_answers.map((answer: string, index: number) => (
                <div key={index} className="bg-gray-50 rounded p-3 text-left">
                  <p className="text-gray-700 leading-relaxed">{answer}</p>
                </div>
              ))}
            </div>
          )}
          
          {/* 新格式：answers字段 */}
          {data.extracted_answers.answers && data.extracted_answers.answers.length > 0 && (
            <div className="space-y-2 text-left">
              {data.extracted_answers.answers.map((answer: string, index: number) => (
                <div key={index} className="bg-gray-50 rounded p-3 text-left">
                  <p className="text-gray-700 leading-relaxed">{answer}</p>
                </div>
              ))}
            </div>
          )}
        </Card>
      )}
    </div>
  )
}

// 技术文档结果组件
function TechnicalResult({ data }: { data: any }) {
  return (
    <div className="space-y-6">
      {data.prerequisites && (
        <Card title="前置条件">
          <div className="space-y-4">
            {/* 可信度标签（完整展示） */}
            {data.prerequisites.confidence !== undefined && (
              <div className="flex items-center gap-2 mb-3">
                <span className="text-sm text-gray-600">可信度：</span>
                <ConfidenceBadge 
                  label={data.prerequisites.confidence_label || '中'} 
                  score={data.prerequisites.confidence}
                />
              </div>
            )}
            
            {data.prerequisites.required && data.prerequisites.required.length > 0 && (
              <div>
                <h4 className="font-medium text-gray-900 mb-2">必须掌握</h4>
                <ul className="list-disc list-inside space-y-1 text-gray-700">
                  {data.prerequisites.required.map((item: string, index: number) => (
                    <li key={index}>{item}</li>
                  ))}
                </ul>
              </div>
            )}
            
            {data.prerequisites.recommended && data.prerequisites.recommended.length > 0 && (
              <div>
                <h4 className="font-medium text-gray-900 mb-2">推荐掌握</h4>
                <ul className="list-disc list-inside space-y-1 text-gray-700">
                  {data.prerequisites.recommended.map((item: string, index: number) => (
                    <li key={index}>{item}</li>
                  ))}
                </ul>
              </div>
            )}
            
            {/* 来源片段（完整展示） */}
            {data.prerequisites.sources && data.prerequisites.sources.length > 0 && (
              <SourceList sources={data.prerequisites.sources} collapsed={false} />
            )}
          </div>
        </Card>
      )}

      {data.learning_path && data.learning_path.length > 0 && (
        <Card title="学习路径">
          <div className="space-y-4 text-left">
            {data.learning_path.map((stage: any, index: number) => (
              <div key={index} className="border-l-4 border-primary-500 pl-4 text-left">
                <div className="flex items-center justify-between mb-2">
                  <h4 className="font-medium text-gray-900">
                    阶段 {stage.stage}: {stage.title}
                  </h4>
                  {/* 可信度标签（完整展示） */}
                  {stage.confidence !== undefined && (
                    <ConfidenceBadge 
                      label={stage.confidence_label || '中'} 
                      score={stage.confidence}
                    />
                  )}
                </div>
                <div className="text-gray-700 leading-relaxed text-left overflow-x-auto">
                  <ReactMarkdown 
                    remarkPlugins={[remarkGfm]}
                    className="prose prose-sm max-w-none prose-headings:text-left prose-p:text-left prose-ul:text-left prose-ol:text-left prose-li:text-left prose-headings:my-4 prose-p:my-3 prose-h1:text-xl prose-h1:font-bold prose-h1:border-b prose-h1:pb-2 prose-h1:mb-3 prose-h2:text-lg prose-h2:font-semibold prose-h2:mt-4 prose-h2:mb-2 prose-h3:text-base prose-h3:font-semibold prose-h3:mt-3 prose-h3:mb-2 prose-table:w-full prose-table:border-collapse prose-th:border prose-th:border-gray-400 prose-th:bg-gray-100 prose-th:p-2 prose-th:text-left prose-th:font-semibold prose-td:border prose-td:border-gray-300 prose-td:p-2 prose-td:text-left prose-ul:my-2 prose-ol:my-2 prose-li:my-1"
                  >
                    {stage.content}
                  </ReactMarkdown>
                </div>
                {/* 来源片段（完整展示） */}
                {stage.sources && stage.sources.length > 0 && (
                  <SourceList sources={stage.sources} collapsed={false} />
                )}
              </div>
            ))}
          </div>
        </Card>
      )}

      {data.learning_methods && (
        <Card title="学习方法建议">
          <div className="space-y-4 text-left">
            {/* 可信度标签（完整展示） */}
            {data.learning_methods.confidence !== undefined && (
              <div className="flex items-center gap-2 mb-3">
                <span className="text-sm text-gray-600">可信度：</span>
                <ConfidenceBadge 
                  label={data.learning_methods.confidence_label || '中'} 
                  score={data.learning_methods.confidence}
                />
              </div>
            )}
            
            {data.learning_methods.theory && (
              <div className="text-left">
                <h4 className="font-medium text-gray-900 mb-2">理论学习</h4>
                <div className="text-gray-700 leading-relaxed text-left overflow-x-auto">
                  <ReactMarkdown 
                    remarkPlugins={[remarkGfm]}
                    className="prose prose-sm max-w-none prose-headings:text-left prose-p:text-left prose-ul:text-left prose-ol:text-left prose-li:text-left prose-headings:my-4 prose-p:my-3 prose-h1:text-xl prose-h1:font-bold prose-h1:border-b prose-h1:pb-2 prose-h1:mb-3 prose-h2:text-lg prose-h2:font-semibold prose-h2:mt-4 prose-h2:mb-2 prose-h3:text-base prose-h3:font-semibold prose-h3:mt-3 prose-h3:mb-2 prose-table:w-full prose-table:border-collapse prose-th:border prose-th:border-gray-400 prose-th:bg-gray-100 prose-th:p-2 prose-th:text-left prose-th:font-semibold prose-td:border prose-td:border-gray-300 prose-td:p-2 prose-td:text-left prose-ul:my-2 prose-ol:my-2 prose-li:my-1"
                    components={{
                      code({ node, inline, className, children, ...props }: any) {
                        const match = /language-(\w+)/.exec(className || '')
                        const codeString = String(children).replace(/\n$/, '')
                        
                        if (!inline && match && match[1] === 'mermaid') {
                          return (
                            <ErrorBoundary>
                              <MermaidRenderer chart={codeString} />
                            </ErrorBoundary>
                          )
                        }
                        
                        return (
                          <code className={className} {...props}>
                            {children}
                          </code>
                        )
                      }
                    }}
                  >
                    {data.learning_methods.theory}
                  </ReactMarkdown>
                </div>
              </div>
            )}
            
            {data.learning_methods.practice && (
              <div className="text-left">
                <h4 className="font-medium text-gray-900 mb-2">实践建议</h4>
                <div className="text-gray-700 leading-relaxed text-left overflow-x-auto">
                  <ReactMarkdown 
                    remarkPlugins={[remarkGfm]}
                    className="prose prose-sm max-w-none prose-headings:text-left prose-p:text-left prose-ul:text-left prose-ol:text-left prose-li:text-left prose-headings:my-4 prose-p:my-3 prose-h1:text-xl prose-h1:font-bold prose-h1:border-b prose-h1:pb-2 prose-h1:mb-3 prose-h2:text-lg prose-h2:font-semibold prose-h2:mt-4 prose-h2:mb-2 prose-h3:text-base prose-h3:font-semibold prose-h3:mt-3 prose-h3:mb-2 prose-table:w-full prose-table:border-collapse prose-th:border prose-th:border-gray-400 prose-th:bg-gray-100 prose-th:p-2 prose-th:text-left prose-th:font-semibold prose-td:border prose-td:border-gray-300 prose-td:p-2 prose-td:text-left prose-ul:my-2 prose-ol:my-2 prose-li:my-1"
                    components={{
                      code({ node, inline, className, children, ...props }: any) {
                        const match = /language-(\w+)/.exec(className || '')
                        const codeString = String(children).replace(/\n$/, '')
                        
                        if (!inline && match && match[1] === 'mermaid') {
                          return (
                            <ErrorBoundary>
                              <MermaidRenderer chart={codeString} />
                            </ErrorBoundary>
                          )
                        }
                        
                        return (
                          <code className={className} {...props}>
                            {children}
                          </code>
                        )
                      }
                    }}
                  >
                    {data.learning_methods.practice}
                  </ReactMarkdown>
                </div>
              </div>
            )}
            
            {/* 来源片段（完整展示） */}
            {data.learning_methods.sources && data.learning_methods.sources.length > 0 && (
              <SourceList sources={data.learning_methods.sources} collapsed={false} />
            )}
          </div>
        </Card>
      )}

      {data.related_technologies && (
        <Card title="相关技术">
          {/* 可信度标签（完整展示） */}
          {data.related_technologies.confidence !== undefined && (
            <div className="flex items-center gap-2 mb-3">
              <span className="text-sm text-gray-600">可信度：</span>
              <ConfidenceBadge 
                label={data.related_technologies.confidence_label || '中'} 
                score={data.related_technologies.confidence}
              />
            </div>
          )}
          
          {/* 技术列表 */}
          {data.related_technologies.technologies && data.related_technologies.technologies.length > 0 && (
            <div className="flex flex-wrap gap-2">
              {data.related_technologies.technologies.map((tech: string, index: number) => (
                <span
                  key={index}
                  className="px-3 py-1 bg-primary-100 text-primary-800 rounded-full text-sm"
                >
                  {tech}
                </span>
              ))}
            </div>
          )}
          
          {/* 兼容旧格式（直接是数组） */}
          {Array.isArray(data.related_technologies) && data.related_technologies.length > 0 && (
            <div className="flex flex-wrap gap-2">
              {data.related_technologies.map((tech: string, index: number) => (
                <span
                  key={index}
                  className="px-3 py-1 bg-primary-100 text-primary-800 rounded-full text-sm"
                >
                  {tech}
                </span>
              ))}
            </div>
          )}
          
          {/* 来源片段（完整展示） */}
          {data.related_technologies.sources && data.related_technologies.sources.length > 0 && (
            <SourceList sources={data.related_technologies.sources} collapsed={false} />
          )}
        </Card>
      )}
    </div>
  )
}

// 架构文档结果组件（弱展示模式）
function ArchitectureResult({ data }: { data: any }) {
  return (
    <div className="space-y-6 text-left">
      {data.config_steps && data.config_steps.length > 0 && (
        <Card title="配置流程">
          <div className="space-y-4 text-left">
            {data.config_steps.map((step: any, index: number) => (
              <div key={index} className="border-l-4 border-primary-500 pl-4 text-left">
                <h4 className="font-medium text-gray-900 mb-2">
                  步骤 {step.step}: {step.title}
                </h4>
                <div className="text-gray-700 leading-relaxed text-left overflow-x-auto">
                  <ReactMarkdown 
                    remarkPlugins={[remarkGfm]}
                    className="prose prose-sm max-w-none prose-headings:text-left prose-p:text-left prose-ul:text-left prose-ol:text-left prose-li:text-left prose-headings:my-4 prose-p:my-3 prose-h1:text-xl prose-h1:font-bold prose-h1:border-b prose-h1:pb-2 prose-h1:mb-3 prose-h2:text-lg prose-h2:font-semibold prose-h2:mt-4 prose-h2:mb-2 prose-h3:text-base prose-h3:font-semibold prose-h3:mt-3 prose-h3:mb-2 prose-table:w-full prose-table:border-collapse prose-th:border prose-th:border-gray-400 prose-th:bg-gray-100 prose-th:p-2 prose-th:text-left prose-th:font-semibold prose-td:border prose-td:border-gray-300 prose-td:p-2 prose-td:text-left prose-ul:my-2 prose-ol:my-2 prose-li:my-1"
                    components={{
                      code({ node, inline, className, children, ...props }: any) {
                        const match = /language-(\w+)/.exec(className || '')
                        const codeString = Array.isArray(children) 
                          ? children.join('') 
                          : String(children).replace(/\n$/, '')
                        
                        // 如果是 Mermaid 代码块，使用 MermaidRenderer
                        if (!inline && match && match[1] === 'mermaid') {
                          return (
                            <ErrorBoundary>
                              <MermaidRenderer chart={codeString} />
                            </ErrorBoundary>
                          )
                        }
                        
                        // 其他代码块使用默认渲染
                        return (
                          <code className={className} {...props}>
                            {children}
                          </code>
                        )
                      }
                    }}
                  >
                    {step.description}
                  </ReactMarkdown>
                </div>
                {/* 可信度和来源（弱展示：默认隐藏） */}
                {(step.confidence !== undefined || (step.sources && Array.isArray(step.sources) && step.sources.length > 0)) && (
                  <WeakDisplay 
                    confidence={step.confidence}
                    confidenceLabel={step.confidence_label}
                    sources={step.sources}
                  />
                )}
              </div>
            ))}
          </div>
        </Card>
      )}

      {data.components && data.components.length > 0 && (
        <Card title="系统组件">
          <div className="space-y-3 text-left">
            {data.components.map((comp: any, index: number) => (
              <div key={index} className="bg-gray-50 rounded p-3 text-left">
                <h4 className="font-medium text-gray-900 mb-2">{comp.name}</h4>
                <p className="text-sm text-gray-700 mb-2 leading-relaxed">{comp.description}</p>
                {comp.dependencies && comp.dependencies.length > 0 && (
                  <div className="text-xs text-gray-500">
                    依赖: {comp.dependencies.join(', ')}
                  </div>
                )}
              </div>
            ))}
          </div>
        </Card>
      )}

      {data.architecture_view && (
        <Card title="组件全景视图">
          <div className="prose max-w-none prose-headings:text-left prose-p:text-left prose-ul:text-left prose-ol:text-left prose-li:text-left prose-headings:my-4 prose-p:my-3 prose-h1:text-2xl prose-h1:font-bold prose-h1:border-b prose-h1:pb-2 prose-h1:mb-4 prose-h2:text-xl prose-h2:font-semibold prose-h2:mt-6 prose-h2:mb-3 prose-h3:text-lg prose-h3:font-semibold prose-h3:mt-4 prose-h3:mb-2 prose-table:w-full prose-table:border-collapse prose-th:border prose-th:border-gray-400 prose-th:bg-gray-100 prose-th:p-3 prose-th:text-left prose-th:font-semibold prose-td:border prose-td:border-gray-300 prose-td:p-3 prose-td:text-left prose-ul:my-3 prose-ol:my-3 prose-li:my-1 text-left overflow-x-auto">
            <ReactMarkdown 
              remarkPlugins={[remarkGfm]}
              components={{
                code({ node, inline, className, children, ...props }: any) {
                        const match = /language-(\w+)/.exec(className || '')
                        const codeString = Array.isArray(children) 
                          ? children.join('') 
                          : String(children).replace(/\n$/, '')
                        
                        // 如果是 Mermaid 代码块，使用 MermaidRenderer
                        if (!inline && match && match[1] === 'mermaid') {
                          return (
                            <ErrorBoundary>
                              <MermaidRenderer chart={codeString} />
                            </ErrorBoundary>
                          )
                        }
                        
                        // 其他代码块使用默认渲染
                        return (
                          <code className={className} {...props}>
                            {children}
                          </code>
                        )
                }
              }}
            >
              {data.architecture_view}
            </ReactMarkdown>
          </div>
        </Card>
      )}

      {data.plain_explanation && (
        <Card title="白话串讲">
          <div className="prose max-w-none prose-headings:text-left prose-p:text-left prose-ul:text-left prose-ol:text-left prose-li:text-left prose-headings:my-4 prose-p:my-3 prose-h1:text-2xl prose-h1:font-bold prose-h1:border-b prose-h1:pb-2 prose-h1:mb-4 prose-h2:text-xl prose-h2:font-semibold prose-h2:mt-6 prose-h2:mb-3 prose-h3:text-lg prose-h3:font-semibold prose-h3:mt-4 prose-h3:mb-2 prose-table:w-full prose-table:border-collapse prose-th:border prose-th:border-gray-400 prose-th:bg-gray-100 prose-th:p-3 prose-th:text-left prose-th:font-semibold prose-td:border prose-td:border-gray-300 prose-td:p-3 prose-td:text-left prose-ul:my-3 prose-ol:my-3 prose-li:my-1 text-left overflow-x-auto">
            <ReactMarkdown 
              remarkPlugins={[remarkGfm]}
              components={{
                code({ node, inline, className, children, ...props }: any) {
                  const match = /language-(\w+)/.exec(className || '')
                  const codeString = String(children).replace(/\n$/, '')
                  
                  // 如果是 Mermaid 代码块，使用 MermaidRenderer
                  if (!inline && match && match[1] === 'mermaid') {
                    return <MermaidRenderer chart={codeString} />
                  }
                  
                  // 其他代码块使用默认渲染
                  return (
                    <code className={className} {...props}>
                      {children}
                    </code>
                  )
                }
              }}
            >
              {data.plain_explanation}
            </ReactMarkdown>
          </div>
        </Card>
      )}

      {data.checklist && (
        <Card title="配置检查清单">
          {/* 可信度和来源（弱展示：默认隐藏） */}
          {data.checklist && typeof data.checklist === 'object' && !Array.isArray(data.checklist) && (
            (data.checklist.confidence !== undefined || (data.checklist.sources && Array.isArray(data.checklist.sources) && data.checklist.sources.length > 0)) && (
              <WeakDisplay 
                confidence={data.checklist.confidence}
                confidenceLabel={data.checklist.confidence_label}
                sources={data.checklist.sources}
              />
            )
          )}
          
          {/* 检查清单列表 */}
          {Array.isArray(data.checklist) && data.checklist.length > 0 && (
            <ul className="space-y-2 text-left">
              {data.checklist.map((item: string, index: number) => (
                <li key={index} className="flex items-start text-left">
                  <input
                    type="checkbox"
                    className="mt-1 mr-2"
                    disabled
                  />
                  <span className="text-gray-700 text-left">{item}</span>
                </li>
              ))}
            </ul>
          )}
          
          {/* 新格式：items字段 */}
          {data.checklist && typeof data.checklist === 'object' && !Array.isArray(data.checklist) && data.checklist.items && Array.isArray(data.checklist.items) && data.checklist.items.length > 0 && (
            <ul className="space-y-2 text-left">
              {data.checklist.items.map((item: string, index: number) => (
                <li key={index} className="flex items-start text-left">
                  <input
                    type="checkbox"
                    className="mt-1 mr-2"
                    disabled
                  />
                  <span className="text-gray-700 text-left">{item}</span>
                </li>
              ))}
            </ul>
          )}
        </Card>
      )}
      
      {/* 相关技术（弱展示） */}
      {data.related_technologies && (
        <Card title="相关技术">
          {/* 可信度和来源（弱展示：默认隐藏） */}
          {data.related_technologies && typeof data.related_technologies === 'object' && !Array.isArray(data.related_technologies) && (
            (data.related_technologies.confidence !== undefined || (data.related_technologies.sources && Array.isArray(data.related_technologies.sources) && data.related_technologies.sources.length > 0)) && (
              <WeakDisplay 
                confidence={data.related_technologies.confidence}
                confidenceLabel={data.related_technologies.confidence_label}
                sources={data.related_technologies.sources}
              />
            )
          )}
          
          {/* 技术列表 */}
          {data.related_technologies && typeof data.related_technologies === 'object' && !Array.isArray(data.related_technologies) && data.related_technologies.technologies && Array.isArray(data.related_technologies.technologies) && data.related_technologies.technologies.length > 0 && (
            <div className="flex flex-wrap gap-2">
              {data.related_technologies.technologies.map((tech: string, index: number) => (
                <span
                  key={index}
                  className="px-3 py-1 bg-primary-100 text-primary-800 rounded-full text-sm"
                >
                  {tech}
                </span>
              ))}
            </div>
          )}
          
          {/* 兼容旧格式（直接是数组） */}
          {Array.isArray(data.related_technologies) && data.related_technologies.length > 0 && (
            <div className="flex flex-wrap gap-2">
              {data.related_technologies.map((tech: string, index: number) => (
                <span
                  key={index}
                  className="px-3 py-1 bg-primary-100 text-primary-800 rounded-full text-sm"
                >
                  {tech}
                </span>
              ))}
            </div>
          )}
          
          {/* 来源片段（完整展示） */}
          {data.related_technologies && typeof data.related_technologies === 'object' && !Array.isArray(data.related_technologies) && data.related_technologies.sources && Array.isArray(data.related_technologies.sources) && data.related_technologies.sources.length > 0 && (
            <SourceList sources={data.related_technologies.sources} collapsed={false} />
          )}
        </Card>
      )}
    </div>
  )
}

