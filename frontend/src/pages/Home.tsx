import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import Button from '../components/ui/Button'
import Card from '../components/ui/Card'
import LoadingSpinner from '../components/ui/LoadingSpinner'
import { historyApi } from '../api/history'
import type { DocumentHistoryItem } from '../types'

export default function Home() {
  const navigate = useNavigate()
  const [recentHistory, setRecentHistory] = useState<DocumentHistoryItem[]>([])
  const [historyLoading, setHistoryLoading] = useState(true)

  // 获取最近的历史记录（最多10条）
  useEffect(() => {
    const fetchRecentHistory = async () => {
      try {
        const data = await historyApi.getHistory({
          page: 1,
          page_size: 10
        })
        setRecentHistory(data.items || [])
      } catch (err) {
        // 静默失败，不影响首页展示
        console.error('获取历史记录失败:', err)
      } finally {
        setHistoryLoading(false)
      }
    }
    fetchRecentHistory()
  }, [])

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'completed':
        return 'bg-green-100 text-green-800'
      case 'processing':
        return 'bg-blue-100 text-blue-800'
      case 'failed':
        return 'bg-red-100 text-red-800'
      default:
        return 'bg-gray-100 text-gray-800'
    }
  }

  const getStatusLabel = (status: string) => {
    switch (status) {
      case 'completed':
        return '已完成'
      case 'processing':
        return '处理中'
      case 'failed':
        return '失败'
      default:
        return '待处理'
    }
  }

  return (
    <div className="max-w-4xl mx-auto space-y-8">
      {/* 顶部主叙事 */}
      <div className="text-center space-y-4">
        <h1 className="text-4xl md:text-5xl font-bold text-gray-900 leading-tight">
          把技术文档，变成你能真正理解的知识
        </h1>
        <p className="text-xl text-gray-600 max-w-2xl mx-auto">
          上传一份文档，先帮你理清结构，再一起规划学习路线
        </p>
      </div>

      {/* 右上角历史记录链接 */}
      <div className="flex justify-end">
        <button
          onClick={() => navigate('/history')}
          className="text-sm text-gray-500 hover:text-primary-600 transition-colors"
        >
          查看历史记录 →
        </button>
      </div>

      {/* 单一主入口 */}
      <Card className="border-2 border-primary-200 bg-gradient-to-br from-primary-50 to-white">
        <div className="text-center space-y-4 py-6">
          <div className="text-5xl mb-2">📄</div>
          <h2 className="text-2xl font-medium text-gray-900">
            上传一份文档开始
          </h2>
          <p className="text-gray-600 max-w-md mx-auto leading-relaxed">
            支持 <span className="font-medium">PDF / Word / PPT</span>
            <br />
            <span className="text-gray-500">先看看文档说了什么，再一起规划怎么学</span>
          </p>
          <div className="pt-2">
            <Button 
              onClick={() => navigate('/upload')} 
              size="lg"
              className="px-8 py-3 text-lg"
            >
              开始理解文档
            </Button>
          </div>
          <p className="text-xs text-gray-400 mt-2 font-normal leading-relaxed">
            我们不是老师，只是你的学习伙伴
          </p>
          {/* 弱入口提示 */}
          {recentHistory.length > 0 && (
            <div className="pt-4 border-t border-gray-200">
              <button
                onClick={() => navigate('/history')}
                className="text-sm text-gray-500 hover:text-primary-600 transition-colors"
              >
                或查看你之前分析过的文档 →
              </button>
            </div>
          )}
        </div>
      </Card>

      {/* "你会得到什么" - 按认知结果分 */}
      <Card>
        <h3 className="font-medium text-gray-900 mb-6 text-center">
          你上传后，我们会一起：
        </h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div className="flex items-start space-x-3">
            <span className="text-2xl flex-shrink-0">🧭</span>
            <div>
              <h4 className="font-normal text-gray-900 mb-1">梳理学习顺序</h4>
              <p className="text-sm text-gray-600 font-normal leading-relaxed">
                帮你理清先看什么、再学什么，不再乱读文档
              </p>
            </div>
          </div>
          <div className="flex items-start space-x-3">
            <span className="text-2xl flex-shrink-0">❓</span>
            <div>
              <h4 className="font-normal text-gray-900 mb-1">提炼关键问题</h4>
              <p className="text-sm text-gray-600 font-normal leading-relaxed">
                帮你整理应该能回答的问题，适合复习和面试
              </p>
            </div>
          </div>
          <div className="flex items-start space-x-3">
            <span className="text-2xl flex-shrink-0">🧩</span>
            <div>
              <h4 className="font-normal text-gray-900 mb-1">解释系统结构</h4>
              <p className="text-sm text-gray-600 font-normal leading-relaxed">
                用更直白的方式解释组件在干嘛
              </p>
            </div>
          </div>
          <div className="flex items-start space-x-3">
            <span className="text-2xl flex-shrink-0">🔍</span>
            <div>
              <h4 className="font-normal text-gray-900 mb-1">支持对话式追问</h4>
              <p className="text-sm text-gray-600 font-normal leading-relaxed">
                基于文档内容和你讨论，而不是胡乱聊天
              </p>
            </div>
          </div>
        </div>
        {/* 弱化技术感，强化安心感 */}
        <div className="mt-6 pt-6 border-t border-gray-200 text-center">
          <div className="flex items-center justify-center space-x-2 text-sm text-gray-400 font-normal">
            <span>⏱️</span>
            <span>每一步都在这里，不会突然卡住</span>
          </div>
        </div>
      </Card>

      {/* 历史记录独立区块 */}
      {recentHistory.length > 0 && (
        <Card>
          <div className="flex items-center justify-between mb-4">
            <h3 className="font-semibold text-gray-900">最近分析的文档</h3>
            <button
              onClick={() => navigate('/history')}
              className="text-sm text-primary-600 hover:text-primary-700 transition-colors"
            >
              查看全部 →
            </button>
          </div>
          
          {historyLoading ? (
            <div className="flex justify-center py-8">
              <LoadingSpinner size="md" />
            </div>
          ) : (
            <div className="space-y-3">
              {recentHistory.slice(0, 5).map((item) => (
                <div
                  key={item.document_id}
                  className="border border-gray-200 rounded-lg p-4 hover:border-primary-300 hover:bg-primary-50 transition-all cursor-pointer"
                  onClick={() => {
                    if (item.status === 'completed') {
                      navigate(`/result/${item.document_id}`)
                    } else if (item.status === 'processing') {
                      navigate(`/progress/${item.document_id}`)
                    }
                  }}
                >
                  <div className="flex items-center justify-between">
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center space-x-2 mb-1">
                        <h4 className="font-medium text-gray-900 truncate">
                          {item.filename}
                        </h4>
                        <span className={`px-2 py-0.5 rounded-full text-xs font-medium flex-shrink-0 ${getStatusColor(item.status)}`}>
                          {getStatusLabel(item.status)}
                        </span>
                        {item.document_type && (
                          <span className="px-2 py-0.5 bg-gray-100 text-gray-700 rounded-full text-xs flex-shrink-0">
                            {item.document_type === 'technical' ? '技术文档' : 
                             item.document_type === 'interview' ? '面试题' : 
                             item.document_type === 'architecture' ? '架构文档' : 
                             item.document_type}
                          </span>
                        )}
                      </div>
                      <div className="flex items-center space-x-4 text-sm text-gray-500">
                        <span>类型: {item.file_type.toUpperCase()}</span>
                        {item.processing_time && (
                          <span>处理时间: {item.processing_time}秒</span>
                        )}
                        <span>{new Date(item.upload_time).toLocaleDateString('zh-CN', { 
                          month: 'short', 
                          day: 'numeric',
                          hour: '2-digit',
                          minute: '2-digit'
                        })}</span>
                      </div>
                    </div>
                    {item.status === 'completed' && (
                      <div className="ml-4 flex-shrink-0">
                        <Button
                          size="sm"
                          variant="secondary"
                          onClick={(e) => {
                            e.stopPropagation()
                            navigate(`/result/${item.document_id}`)
                          }}
                        >
                          查看结果
                        </Button>
                      </div>
                    )}
                  </div>
                </div>
              ))}
              {recentHistory.length > 5 && (
                <div className="text-center pt-2">
                  <button
                    onClick={() => navigate('/history')}
                    className="text-sm text-primary-600 hover:text-primary-700 transition-colors"
                  >
                    还有 {recentHistory.length - 5} 条记录，查看全部 →
                  </button>
                </div>
              )}
            </div>
          )}
        </Card>
      )}
    </div>
  )
}

